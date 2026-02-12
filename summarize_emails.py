import imaplib
import email
from datetime import datetime, timedelta
import subprocess
import os
import tempfile

# 配置信息
imap_server = "mail.cstnet.cn"
imap_port = 993
username = "yahan@iscas.ac.cn"
password = "IMh7!~wdi39&aE2b"

# 要检查的邮箱文件夹
FOLDERS = ["INBOX", "v8-riscv", "v8-dev", "riscv"]


def get_unread_since_yesterday(folder_name):
    """获取指定文件夹中从昨天00:00开始的邮件（只读模式）"""
    try:
        mail = imaplib.IMAP4_SSL(imap_server, imap_port)
        mail.login(username, password)

        # 选择文件夹（只读模式）
        status, data = mail.select(folder_name, readonly=True)
        if status != 'OK':
            print(f"  选择文件夹 {folder_name} 失败")
            mail.logout()
            return []

        # 计算昨天的日期
        yesterday = datetime.now() - timedelta(days=1)
        yesterday_str = yesterday.strftime("%d-%b-%Y")

        # 搜索邮件（只按日期筛选）
        status, data = mail.search(None, f'SINCE {yesterday_str}')
        mail_ids = data[0].split() if data and data[0] else []

        emails = []
        for mail_id in mail_ids:
            status, msg_data = mail.fetch(mail_id, '(RFC822 FLAGS)')
            if status != 'OK':
                continue

            raw_email = msg_data[0][1]
            msg = email.message_from_bytes(raw_email)

            subject = msg.get('Subject', '(无主题)')
            from_header = msg.get('From', '(未知)')
            date_header = msg.get('Date', '(未知)')

            # 提取正文
            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    content_type = part.get_content_type()
                    content_disposition = str(part.get('Content-Disposition'))
                    if content_type == 'text/plain' and 'attachment' not in content_disposition:
                        try:
                            body = part.get_payload(decode=True).decode(part.get_content_charset() or 'utf-8', errors='replace')
                        except:
                            body = part.get_payload(decode=True).decode('utf-8', errors='replace')
                        break
            else:
                if msg.get_content_type() == 'text/plain':
                    try:
                        body = msg.get_payload(decode=True).decode(msg.get_content_charset() or 'utf-8', errors='replace')
                    except:
                        body = msg.get_payload(decode=True).decode('utf-8', errors='replace')

            emails.append({
                'folder': folder_name,
                'subject': subject,
                'from': from_header,
                'date': date_header,
                'body': body
            })

        mail.close()
        mail.logout()

        return emails

    except Exception as e:
        print(f"  IMAP 错误 ({folder_name}): {e}")
        return []


def summarize_with_claude(all_emails):
    """使用 Claude Code CLI 总结邮件"""
    if not all_emails:
        print("没有未读邮件需要总结")
        return

    # 按文件夹分组
    folders = {}
    for email_data in all_emails:
        folder = email_data['folder']
        if folder not in folders:
            folders[folder] = []
        folders[folder].append(email_data)

    # 构建提示
    prompt = "请总结以下邮件，按文件夹分组，按重要性排序。对于每封邮件，列出：\n"
    prompt += "1. 发件人、主题、日期\n"
    prompt += "2. 邮件的完整正文内容\n"
    prompt += "3. 需要采取的具体行动\n\n"
    prompt += "邮件内容如下：\n\n"

    for folder, emails in folders.items():
        prompt += f"=== {folder} (共 {len(emails)} 封) ===\n"
        for i, email_data in enumerate(emails, 1):
            prompt += f"---\n"
            prompt += f"邮件 {i}:\n"
            prompt += f"发件人: {email_data['from']}\n"
            prompt += f"主题: {email_data['subject']}\n"
            prompt += f"日期: {email_data['date']}\n"
            prompt += f"\n正文:\n{email_data['body']}\n"
            prompt += f"\n"
        prompt += "\n"

    prompt += "请用中文详细总结，包括所有邮件的具体内容、讨论的技术问题、代码审查的细节、以及需要采取的行动（如需回复、审批、参加会议等）。"

    # 通过 stdin 传递 prompt
    try:
        result = subprocess.run(
            ['claude', '--print'],
            input=prompt,
            capture_output=True,
            text=True,
            timeout=180
        )

        if result.returncode == 0:
            print("\n" + "="*60)
            print("邮件总结")
            print("="*60)
            print(result.stdout)
        else:
            print(f"Claude CLI 错误: {result.stderr}")

    except FileNotFoundError:
        print("错误: 未找到 Claude Code CLI")
    except subprocess.TimeoutExpired:
        print("错误: Claude API 调用超时")


def main():
    print("正在检查邮件...\n")

    yesterday = datetime.now() - timedelta(days=1)
    yesterday_str = yesterday.strftime("%Y-%m-%d")
    print(f"搜索范围: 从 {yesterday_str} 00:00 至今 (只读模式，不修改未读标记)\n")

    all_emails = []
    for folder in FOLDERS:
        print(f"检查文件夹: {folder}...")
        emails = get_unread_since_yesterday(folder)
        if emails:
            print(f"  找到 {len(emails)} 封邮件")
            all_emails.extend(emails)
        else:
            print(f"  未找到邮件")

    print(f"\n总计: {len(all_emails)} 封邮件\n")

    if all_emails:
        summarize_with_claude(all_emails)
    else:
        print("没有找到邮件")


if __name__ == "__main__":
    main()
