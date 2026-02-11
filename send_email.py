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

def fetch():
    srcdir = os.path.join(CWD, "v8")
    if os.path.isdir(srcdir):
        # We already have a checked out version of v8, so we assume it is already
        # on the main branch and just pull there.
        _exec(["git", "pull", "origin", "main"], cwd=srcdir)
    else:
        # We do not have a checkout of v8 yet, so we use 'fetch' to get the initial
        # version of it and make sure to change to the main branch.
        _exec(["git", "clone", "--filter=blob:none", "--no-checkout", "https://github.com/v8/v8.git"])
        _exec(["git", "checkout", "main"], cwd=srcdir)

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
    #
    # V8 引擎更新邮件
    #
    # 读取 v8_update_summary.md 文件内容
    summary_file = os.path.join(CWD, "v8_update_summary.md")
    with open(summary_file, "r", encoding="utf-8") as f:
        email_body = f.read()

    msg = MIMEText(markdown.markdown(email_body, extensions=['tables']), "html", "utf-8")
    msg['From'] = sender
    msg['To'] = receiver
    msg['Subject'] = Header(f"V8每日改动总结 - {datetime.now().strftime('%Y-%m-%d')}", "utf-8")

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
    fetch()
    output = _exec(["git", "log", "--since='24 hours ago'"], cwd=os.path.join(CWD, "v8"), echo_output=False, capture_output=True)
    with open(os.path.join(CWD, "v8_log.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(output))
    _exec(["/usr/local/bin/claude", "-p", 
         f"读取v8_log.txt, 总结V8过去24小时的更新内容, 先列出改动重点及大概情况介绍，后列出改动主要内容、时间、作者、Reviewed-on URL, 并写入到{CWD}/v8_update_summary.md中", 
         "--permission-mode", "acceptEdits"])
    send_secure_email()
