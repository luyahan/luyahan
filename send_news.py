import os
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from email.header import Header
import shutil
import subprocess
import sys
import markdown



CWD = os.path.join("/home/luyahan/source/luyahan")
_last_cwd = CWD
# Helper function that runs a command given by the arguments in a subprocess.
# Notice that we default to checking that it runs successfully and we show
# useful information about the working directory.
def _exec(arguments, cwd=CWD, check=True, echo_output=True, capture_output=False):
    global _last_cwd
    if cwd != _last_cwd:
        print("+ " + "cd " + cwd, flush=True)
        _last_cwd = cwd
    # Extend the PATH of the subprocess, so the correct depot_tools are used.
    # This is necessary at least when calling out to tools/run-tests.py.
    env = dict(os.environ)
    # If we're capturing the output, we redirect stderr to stdout and ask
    # the subprocess to pipe stdout to us.
    stdout = None
    stderr = None
    if capture_output:
        stdout = subprocess.PIPE
        stderr = subprocess.STDOUT
    elif not echo_output:
        stdout = subprocess.DEVNULL
        stderr = subprocess.STDOUT
    # Run the subprocess.
    commandline = " ".join([f"'{x}'" if " " in x else x for x in arguments])
    print(f"+ {commandline}", flush=True)
    process = subprocess.Popen(
        arguments,
        cwd=cwd,
        env=env,
        stderr=stderr,
        stdout=stdout,
        text=True)
    # Capture the output (if necessary) and write it to stdout as we go along.
    output = None
    if capture_output:
        output = []
        for line in process.stdout:
            if echo_output: sys.stdout.write(line)
            output.append(line.rstrip())
    # Wait for the subprocess to terminate and optionally check if the
    # exit code indicates success.
    retcode = process.wait()
    if check and retcode != 0:
        raise subprocess.CalledProcessError(retcode, arguments)
    return output

def send_secure_email():
    # 从环境变量获取授权码
    # 如果环境变量不存在，getenv 会返回 None，避免脚本崩溃
    auth_code = os.getenv('EMAIL_AUTH_CODE')
    
    if not auth_code:
        print("错误：请先设置环境变量 EMAIL_AUTH_CODE")
        return

    # 配置信息
    smtp_server = "smtp.gmail.com"  # 以 QQ 邮箱为例
    sender = "luyahan.lu@gmail.com"
    receiver = "yahan@iscas.ac.cn"

    # 邮件对象
    # 读取 news.md 文件内容
    summary_file = os.path.join(CWD, "news.md")
    with open(summary_file, "r", encoding="utf-8") as f:
        email_body = f.read()

    msg = MIMEText(markdown.markdown(email_body, extensions=['tables']), "html", "utf-8")
    msg['From'] = sender
    msg['To'] = receiver
    msg['Subject'] = Header(f"今日新闻总结 - {datetime.now().strftime('%Y-%m-%d')}", "utf-8")

    try:
        # 使用 SSL 连接
        with smtplib.SMTP_SSL(smtp_server, 465) as server:
            # 登录
            server.login(sender, auth_code)
            # 发送
            server.sendmail(sender, [receiver], msg.as_string())
        print("🚀 邮件已成功寄出！")
    except Exception as e:
        print(f"❌ 发送失败，原因：{e}")

if __name__ == "__main__":
    _exec(["/usr/local/bin/claude", "-p", 
         f"帮我总结今日时政、财经、科技新闻, 并写入到{CWD}/news.md中", 
         "--permission-mode", "acceptEdits"])
    send_secure_email()
