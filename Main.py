from flask import Flask, request, abort
import os

#JSONファイルを扱うのに必要
import json

#ユーザー情報の取得に必要
import urllib

#日付情報の取得に必要
from datetime import datetime

from cmddata import lesson

from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage, MemberJoinedEvent, QuickReplyButton, QuickReply, MessageAction, TemplateSendMessage, ButtonsTemplate,
)

app = Flask(__name__)

#環境変数取得
YOUR_CHANNEL_ACCESS_TOKEN = os.environ["YOUR_CHANNEL_ACCESS_TOKEN"]
YOUR_CHANNEL_SECRET = os.environ["YOUR_CHANNEL_SECRET"]

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
    elif cmd == "-プロフィール取得":
        #profile = line_bot_api.get_profile(event.source.user_id)
        profile = line_bot_api.get_group_member_profile(event.source.group_id, event.source.user_id)
        #status_msg = profile.status_message
        #if status_msg != "None":
           # LINEに登録されているstatus_messageが空の場合は、"なし"という文字列を代わりの値とする
           #status_msg = "なし"

        messages = TemplateSendMessage(alt_text="Buttons template",
                                       template=ButtonsTemplate(
                                           thumbnail_image_url=profile.picture_url,
                                           title=profile.display_name,
                                           text=f"User ID: {profile.user_id[:10]}..."
                                                #f"Status Message: {status_msg}",
                                           actions=[MessageAction(label="User IDを取得", text=profile.user_id)]))
        line_bot_api.reply_message(event.reply_token, messages=messages)
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
マナーを守って、学力向上に努めましょう\uDBC0\uDC79""".format(json_result["displayName"])))



if __name__ == "__main__":
#    app.run()
    port = int(os.getenv("PORT"))
    app.run(host="0.0.0.0", port=port)
