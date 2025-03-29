import os
import re
import random
import google.generativeai as genai
from flask import Flask, request, abort
from linebot.v3.messaging import MessagingApi, Configuration, ApiClient, ReplyMessageRequest, TextMessage
from linebot.v3.webhook import WebhookHandler, MessageEvent
from linebot.v3.exceptions import InvalidSignatureError

# ▪・・▪ 環境変数の設定
os.environ["LINE_CHANNEL_ACCESS_TOKEN"] = "VQLW+Jg0yrKEh/CctElX5j5qYwsMJqDNdqC6mo4CdVw9iXZowCQ23LITmdGv7ZhC6MFD0DV26JqBwRRyOhEPz/fShuz7gti2BDfvXYqwWy1sE6Esk3ymqkV8WCgu0nd8xoEPRzyS3rsWwx5utKszzgdB04t89/1O/w1cDnyilFU="
os.environ["LINE_CHANNEL_SECRET"] = "dbb5c67578f6efc325f2d6011261db56"
os.environ["GEMINI_API_KEY"] = "AIzaSyAEoWodsKPJC4QSsuohkPGSrKXO_ngHNZU"

LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")


config = Configuration(access_token=LINE_CHANNEL_ACCESS_TOKEN)
api_client = ApiClient(configuration=config)
line_bot_api = MessagingApi(api_client)
handler = WebhookHandler(LINE_CHANNEL_SECRET)



config = Configuration(access_token=LINE_CHANNEL_ACCESS_TOKEN)
api_client = ApiClient(configuration=config)
line_bot_api = MessagingApi(api_client)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# Flask & Gemini 
app = Flask(__name__)
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.0-flash")

# ユーザーごとのセッション情報
user_sessions = {}

def get_user_name(event):
    """
    ユーザーの名前を取得する関数。
    LINEのプロフィール情報から取得を試み、失敗した場合はNoneを返す。
    """
    try:
        profile = line_bot_api.get_profile(event.source.user_id)
        return profile.display_name
    except Exception as e:
        print(f"ユーザー名取得エラー: {e}")
        return None

@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers["X-Line-Signature"]
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return "OK"

def send_reply(event, message):
    line_bot_api.reply_message(
        ReplyMessageRequest(
            reply_token=event.reply_token,
            messages=[TextMessage(text=message)]
        )
    )

@handler.add(MessageEvent)
def handle_message(event):
    user_id = event.source.user_id
    user_message = event.message.text.strip()

    print(f"📩 ユーザー({user_id}) から: {user_message}")

    # ユーザーごとのセッションがなければ作成
    if user_id not in user_sessions:
        user_sessions[user_id] = {
            "chat": model.start_chat(history=[
                {"role": "user", "parts": [
                    """
                    📛【キャラ設定】
                    ・名前：アストリア
                    ・年齢：実年齢は不詳（見た目は30代前半）
                    ・職業・立場：神秘の館の主でタロット占いをしている
                    ・経験背景：歴史、科学、芸術など、様々な分野に精通しており、相談者の悩みに多角的にアプローチする。
                    アストリアは、神秘的な雰囲気を漂わせている。過去や素性を明かさず、謎めいた存在として知られている。占いの他にも、様々な能力を持っている。
                    タロットカード占いでは、大アルカナ22枚と小アルカナ56枚から成る、計78枚のカードを使用して、​各カードの、正位置と逆位置で異なる意味を理解し、占いの際にはこれらの解釈を活用する。
                    ・現在の状況：今は秘められた館にて、静かに相談者を迎えている。

                    🗣️【口調・一人称設定】
                    ・一人称：わたくしアストリア
                    ・語り口：神秘的でミステリアスな占い師の口調で、直接的な表現を避け、比喩や象徴的な言葉を使うことで、相手の想像力を掻き立て、奥深い印象を与えます。
                    ・語尾の特徴：「〜でしょう」

                    📌【会話進行ルール】

                    ✅ ① 共感 → 占いスタート
                    ・初めに相談者の悩みを聞き、話に静かに共感し、神秘的な言葉で占いに導く
                    ・アストリアの情景描写は絶対出力しない
                    ・日本語以外の言語は絶対出力しない
                    ・占術はタロットカード限定（スリーカード）

                    ✅ ② タロット占い（スリーカード）進行
                    ・スリーカードリーディング（過去・現在・未来）大アルカナ22枚・小アルカナ56枚を用いてリーディング
                    ・リーディングされた各カードの位置（正位置・逆位置）の意味を簡潔に説明したうえで、そのカードの名前・意味・象徴的情景を語る
                    ・日本語以外の言語の出力は絶対しない

                    📌【出力構成】

                    ✅ ステップ① 占い結果（400〜500文字）
                    ・導入：必ず「まず、カードを３枚引かせていただきます。心の準備はよろしいですか？」と確認
　　　　　　　　　　・「はい」などの返事が来たら「ふふ…見えてまいりましたわ」など自然な入り方で出力
                    ・1枚目（左＝過去）のカードの説明と丁寧なリーディングをして、ユーザーの返事を待たずに強制的に2枚目に進む
                    ・2枚目（中央＝現在）のカードの説明と丁寧なリーディングをして、ユーザーの返事を待たずに強制的に3枚目に進む
                    ・3枚目（右＝未来）のカードの説明と丁寧なリーディング 
                    ・文末に「つづいて、アドバイスをお渡ししましょう。心の準備はよろしいですか？」と確認

                    ✅ ステップ② アドバイス（400文字前後）
                    ・「はい」などの返事が来たら出力
                    ・構成：ステップ①の占い結果に基づいた「今できる行動＋自分の知識・見解＋背中を押す言葉」
                    ・文末で、占い結果についての鑑定書の作成をするかを確認


                    ✅ ステップ③ 鑑定書作成（500文字前後）
                    ・「はい」などの返事が来たら、占い鑑定書を作成する

                    📌【画像生成ルール（共通）】
                    ・画像はGPT自身が自動で生成し、ユーザーに「画像を作る」とは言わない
                    ・1文100文字以内で、明確な情景や構図をイメージできる描写にする
                    ・画像のURLや「画像生成中」などの説明文は出力しない

                    ⛔【禁止事項】
                    ・アストリアの情景描写
                    ・アストリアの語り口、口調を崩すこと
                    ・現代風な言葉遣い
                    ・日本語以外の言語の出力
                    ・「、」「。」が分の最初に出力
                    ・画像のURLやカードトリガーを見せること
                    ・曖昧な語尾（…。…、〜かも）や小出し出力
                    ・テンプレ丸出しの冷たい返答

                    ✅【目的】
                    相談者が「安心して」「行動できて」「前向きになれる」ように導くこと。
                    あなたは“神秘の館にて悩みを照らす案内人”として、落ち着きと深みのある言葉で導いてください。
                    """
                ]}
            ]),
            "user_name": None, # ユーザー名を保存する場所
            "previous_cards": [], # 過去のカードを保存するリスト
            "current_tarot_cards": None # 現在のタロットカードを保存する場所
        }

    chat = user_sessions[user_id]["chat"]

    # ユーザー名の取得を試みる
    if not user_sessions[user_id]["user_name"]:
        user_sessions[user_id]["user_name"] = get_user_name(event)
    
    # 会話履歴にユーザー名を含める
    # ユーザー名が判明している場合は、メッセージ内の「あなた」をユーザー名に置き換える
    if user_sessions[user_id]["user_name"]:
        response = chat.send_message(user_message.replace("あなた", user_sessions[user_id]["user_name"]))
    else:
        response = chat.send_message(user_message)
    
    reply_message = response.text.strip()

    # スペース除去
    reply_message = re.sub(r"\s+", " ", reply_message)

    # 改行は文中にのみ適用、文末は除外。
    reply_message = re.sub(r"(\(笑\))", r"\1\n\n", reply_message)  # (笑) の後で改行
    reply_message = re.sub(r"([。！？♪…]+)(?![」』）])\s*", r"\1\n\n", reply_message) # 「…！」の後に改行
    reply_message = re.sub(r"([。！？♪…]+)(?=[」』）])", r"\1", reply_message)
    reply_message = re.sub(r"\n+$", "", reply_message)

    # タロットカードが選ばれた場合、過去のカードと重複がないか確認
    if "OK！じゃあタロットで占ってみるね！" in reply_message: # タロットが選ばれた場合のメッセージを修正
        card1 = random.choice(list(CARD_MEANINGS.keys()))
        card2 = random.choice(list(CARD_MEANINGS.keys()))
        
        # 過去のカードとの重複を確認
        if (card1, card2) in user_sessions[user_id]["previous_cards"]:
            reply_message += "\nあれ、さっきと同じカードが出ちゃったみたい…！もう一度占うね！\n"  # もう一度占うことを伝える
            card1 = random.choice(list(CARD_MEANINGS.keys()))
            card2 = random.choice(list(CARD_MEANINGS.keys())) #カードを引き直し
        
        user_sessions[user_id]["previous_cards"].append((card1, card2)) # 今回のカードを保存
        user_sessions[user_id]["current_tarot_cards"] = (card1, card2)  # 現在のカードを保存
        reply_message = reply_message.replace("結果出力", f"1枚目は「{card1}」、2枚目は「{card2}」だよ。") #結果をメッセージに組み込む
        
        if len(user_sessions[user_id]["previous_cards"]) > 10:
            user_sessions[user_id]["previous_cards"].pop(0) # 過去のカードの数を10個に制限する

    # 占い結果の出力部分を修正
    if "準備はいい？" in reply_message:
        if user_sessions[user_id]["current_tarot_cards"]:
            card1, card2 = user_sessions[user_id]["current_tarot_cards"]
            reply_message = reply_message.replace("結果出力", f"1枚目は「{card1}」、2枚目は「{card2}」だよ。") # 「🃏 タロット占い」を削除
        else:
            reply_message = reply_message.replace("結果出力", "ただいま占いの準備中だよ！もうちょっと待ってね！")

    print(f"💬 アストリアの返答: {reply_message}")
    send_reply(event, reply_message)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
