from flask import Flask, request, abort
import os

import time

#JSONファイルを扱うのに必要
import json

#ユーザー情報の取得に必要
import urllib

#日付情報の取得に必要
from datetime import datetime, timezone, timedelta

import pytz

try:
    import MySQLdb
except:
    import pymysql
    pymysql.install_as_MySQLdb()
    import MySQLdb

from cmddata import lesson

from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage, MemberJoinedEvent, QuickReplyButton, QuickReply, MessageAction, TemplateSendMessage, ButtonsTemplate, FollowEvent,
)

app = Flask(__name__)

#環境変数取得
YOUR_CHANNEL_ACCESS_TOKEN = os.environ["YOUR_CHANNEL_ACCESS_TOKEN"]
YOUR_CHANNEL_SECRET = os.environ["YOUR_CHANNEL_SECRET"]

REMOTE_HOST = os.environ['REMOTE_HOST']
REMOTE_DB_NAME = os.environ['REMOTE_DB_NAME']
REMOTE_DB_USER = os.environ['REMOTE_DB_USER']
REMOTE_DB_PASS = os.environ['REMOTE_DB_PASS']
REMOTE_DB_TB = os.environ['REMOTE_DB_TB']

line_bot_api = LineBotApi(YOUR_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(YOUR_CHANNEL_SECRET)

@app.route("/")
def hello_world():
    return "hello world!"

@app.route("/callback", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'

#コマンド
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    cmd = event.message.text
    if not cmd.startswith("-"): return
    if cmd == "-日付":
        text=datetime.now().strftime('今日は%Y年%m月%d日です')
    elif cmd == "-時間割":
        day_list = ["月", "火", "水", "木", "金"]
        items = [QuickReplyButton(action=MessageAction(label=f"{day}", text=f"-{day}曜日の時間割")) for day in day_list]
        messages = TextSendMessage(text="何曜日の時間割ですか？",quick_reply=QuickReply(items=items))
        line_bot_api.reply_message(event.reply_token, messages=messages)
    elif cmd in lesson:
        line_bot_api.reply_message(
            event.reply_token,
            TextMessage(text=lesson[cmd])
        )
    elif cmd == "-DebugProfileG":
        profile = line_bot_api.get_group_member_profile(event.source.group_id, event.source.user_id)
        messages = TemplateSendMessage(alt_text="Buttons template",
                                       template=ButtonsTemplate(
                                           thumbnail_image_url=profile.picture_url,
                                           title=profile.display_name,
                                           text=f"User ID: {profile.user_id[:10]}...",
                                           actions=[MessageAction(label="User IDを取得", text=profile.user_id)]))
        line_bot_api.reply_message(event.reply_token, messages=messages)
    elif cmd == "-ForceSQL":
        utc = datetime.now()
        jst_modify = timedelta(hours=9)
        reply_token = event.reply_token
        user_id = event.source.user_id
        profiles = line_bot_api.get_profile(user_id)
        display_name = profiles.display_name
        picture_url = profiles.picture_url
        status_message = profiles.status_message
        jst = utc+jst_modify
        time_info = jst.strftime('%Y/%m/%d %H:%M:%S')

    # DBへの保存
        try:
            conn = MySQLdb.connect(user=REMOTE_DB_USER, passwd=REMOTE_DB_PASS, host=REMOTE_HOST, db=REMOTE_DB_NAME, use_unicode=True, charset="utf8")
            c = conn.cursor()
            sql = "SELECT `user_id` FROM`"+REMOTE_DB_TB+"` WHERE `user_id` = '"+user_id+"';"
            c.execute(sql)
            ret = c.fetchall()
            if len(ret) == 0:
                sql = "INSERT INTO `"+REMOTE_DB_TB+"` (`user_id`, `display_name`, `picture_url`, `status_message`, `date`)\
                  VALUES ('"+user_id+"', '"+str(display_name)+"', '"+str(picture_url)+"', '"+str(status_message)+"', '"+time_info+"');"
            elif len(ret) == 1:
                sql = "UPDATE `"+REMOTE_DB_TB+"` SET `display_name` = '"+str(display_name)+"', `picture_url` = '"+str(picture_url)+"',\
                `status_message` = '"+str(status_message)+"', `date` = '"+time_info+"' WHERE `user_id` = '"+user_id+"';"
            c.execute(sql)
            conn.commit()
        finally:
            c.close()
            conn.close()
    elif cmd == "-DebugProfileP":
        profile = line_bot_api.get_profile(event.source.user_id)

        status_msg = profile.status_message
        if status_msg != "None":
           status_msg = "なし"

        messages = TemplateSendMessage(alt_text="Buttons template",
                                       template=ButtonsTemplate(
                                           thumbnail_image_url=profile.picture_url,
                                           title=profile.display_name,
                                           text=f"User ID: {profile.user_id[:10]}...\n"
                                                f"Status Message: {status_msg}",
                                           actions=[MessageAction(label="User IDを取得", text=profile.user_id)]))
        line_bot_api.reply_message(event.reply_token, messages=messages)
    elif cmd == "-Push":
        user_id = "Udadd289ae892a95ac0ebcf9d7bc9d550"

        messages = TextSendMessage(text=f"こんにちは😁\n\n最近はいかがお過ごしでしょうか?")
        line_bot_api.push_message(user_id, messages=messages)
    else:
        text=cmd + "コマンドは存在しません"
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=text))

#ユーザーネームを含んだ挨拶
@handler.add(MemberJoinedEvent)
def handle_join(event):
    #参加イベント情報から「ユーザーID」と「グループID」を取得
    uId = event.joined.members[0].user_id
    gId = event.source.group_id
    #LINEのAPIから「ユーザーID」と「グループID」をもとに「ユーザー情報」を取得
    url = 'https://api.line.me/v2/bot/group/{}/member/{}'.format(gId, uId);
    headers = {
        'Content-Type': 'application/json; charset=UTF-8',
        'Authorization': 'Bearer ' + YOUR_CHANNEL_ACCESS_TOKEN,
    }

    req = urllib.request.Request(url, None, headers)
    with urllib.request.urlopen(req) as res:
        response = res.read()
    json_result = json.loads(response.decode('utf-8'))
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text="""{}さんが解答作成部に参加しました！

ノートからルールのご確認をよろしくお願いします\uDBC0\uDC2D
確認後「いいね」してください！

マナーを守って、学力向上に努めましょう\uDBC0\uDC79

公式BOTの友達追加もよろしくお願いします！""".format(json_result["displayName"])))

@handler.add(FollowEvent)
def on_follow(event):
    utc = datetime.now()
    jst_modify = timedelta(hours=9)
    reply_token = event.reply_token
    user_id = event.source.user_id
    profiles = line_bot_api.get_profile(user_id)
    display_name = profiles.display_name
    picture_url = profiles.picture_url
    status_message = profiles.status_message
    jst = utc+jst_modify
    time_info = jst.strftime('%Y/%m/%d %H:%M:%S')

    # DBへの保存
    try:
        conn = MySQLdb.connect(user=REMOTE_DB_USER, passwd=REMOTE_DB_PASS, host=REMOTE_HOST, db=REMOTE_DB_NAME, use_unicode=True, charset="utf8")
        c = conn.cursor()
        sql = "SELECT `user_id` FROM`"+REMOTE_DB_TB+"` WHERE `user_id` = '"+user_id+"';"
        c.execute(sql)
        ret = c.fetchall()
        if len(ret) == 0:
            sql = "INSERT INTO `"+REMOTE_DB_TB+"` (`user_id`, `display_name`, `picture_url`, `status_message`, `date`)\
              VALUES ('"+user_id+"', '"+str(display_name)+"', '"+str(picture_url)+"', '"+str(status_message)+"', '"+time_info+"');"
        elif len(ret) == 1:
            sql = "UPDATE `"+REMOTE_DB_TB+"` SET `display_name` = '"+str(display_name)+"', `picture_url` = '"+str(picture_url)+"',\
            `status_message` = '"+str(status_message)+"', `date` = '"+time_info+"' WHERE `user_id` = '"+user_id+"';"
        c.execute(sql)
        conn.commit()
    finally:
        c.close()
        conn.close()

@app.route('/push_homework_day', methods=['GET'])
def push_homework_day():
    push_text = '今日の小テストは「'
 
    # ゴミの日リスト(1)
    # 0: 月, 1: 火, 2: 水, 3: 木, 4: 金
    homework_list = {
        0: '数学',
        1: '物理',
        2: '体育',
        3: '家庭科',
        4: '道徳',
    }
 
    weekday = datetime.now().weekday()
 
    if weekday == 5 or weekday == 6:
        return 'OK'
 
    push_text += homework_list[weekday] + '」です。\n※テスト配信です。'
    
    conn = MySQLdb.connect(user=REMOTE_DB_USER, passwd=REMOTE_DB_PASS, host=REMOTE_HOST, db=REMOTE_DB_NAME, use_unicode=True, charset="utf8")
    c = conn.cursor()
    sql = "SELECT `user_id` FROM`"+REMOTE_DB_TB+"` ;"
    c.execute(sql)
    
    while True:
        res = c.fetchone()

        if res is None :
            break    

        to = res[0]
        #to = 'Udadd289ae892a95ac0ebcf9d7bc9d550' # 送信先(2)
        line_bot_api.push_message(to, TextSendMessage(text=push_text))


    return 'OK'

if __name__ == "__main__":
#    app.run()
    port = int(os.getenv("PORT"))
    app.run(host="0.0.0.0", port=port)
