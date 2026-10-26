from flask import Flask, request, jsonify
import requests
import re
import os

app = Flask(__name__)

# ==========================================
# إعدادات Evolution API الحقيقية (حط بياناتك هنا)
# ==========================================
EVOLUTION_API_URL = "https://your-evolution-api-server.com"  # رابط سيرفرك
EVOLUTION_API_KEY = "YOUR_API_KEY_HERE"                      # مفتاح الـ API
INSTANCE_NAME = "MyBotInstance"                              # اسم الـ Instance

# ==========================================
# قواعد الحظر والفلترة المتقدمة
# ==========================================
BAD_WORD_PATTERNS = [
    r"أ?ح\s*[aأىيئإء]*",       # احا ومطاتها والمسافات
    r"خر\s*[هةإء]*",         # خرة ومطاتها
    r"فش\s*[خخ]*",         # فشخ ومطاتها
]

STRICT_BAD_EMOJIS = ["🖕"]
BANNED_MEDIA_HASHES = ["patrick_funny_sticker_hash_xyz"]

def normalize_text(text):
    if not text:
        return ""
    text = re.sub(r'[\u064b-\u0652]', '', text)
    return text.strip()

def check_group_message(message_data):
    message_type = message_data.get('messageType', '')
    message_content = message_data.get('message', {})
    
    # فحص الملصقات
    if message_type in ['stickerMessage', 'sticker'] or 'stickerMessage' in message_content:
        sticker_info = message_content.get('stickerMessage', message_content)
        media_hash = sticker_info.get('fileSha256', '') or sticker_info.get('mediaKey', '')
        if media_hash in BANNED_MEDIA_HASHES:
            return False, "ملصق محظور"

    # استخراج النص
    text_body = ""
    if isinstance(message_content, dict):
        text_body = (
            message_content.get('conversation', '') or
            message_content.get('extendedTextMessage', {}).get('text', '') or
            message_content.get('textMessage', {}).get('text', '') or
            message_data.get('body', '')
        )
    elif isinstance(message_content, str):
        text_body = message_content

    if not text_body:
        return True, "نظيف"

    cleaned_text = normalize_text(text_body)

    for pattern in BAD_WORD_PATTERNS:
        if re.search(pattern, cleaned_text, re.IGNORECASE):
            return False, "لفظ ممنوع أو ممدود"
            
    for emoji in STRICT_BAD_EMOJIS:
        if emoji in cleaned_text:
            return False, "إيموجي مسيء"
            
    return True, "الرسالة نظيفة"

def delete_whatsapp_message(remote_jid, message_id):
    try:
        url = f"{EVOLUTION_API_URL}/chat/deleteMessage/{INSTANCE_NAME}"
        headers = {
            "apikey": EVOLUTION_API_KEY,
            "Content-Type": "application/json"
        }
        payload = {
            "remoteJid": remote_jid,
            "id": message_id,
            "fromMe": False
        }
        response = requests.post(url, json=payload, headers=headers)
        if response.status_code in [200, 201]:
            print("✅ تم حذف الرسالة بنجاح للجميع!")
        else:
            print(f"⚠️ فشل الحذف: {response.text}")
    except Exception as e:
        print(f"خطأ أثناء الاتصال بـ API الحذف: {e}")

@app.route('/webhook', methods=['POST'])
def whatsapp_webhook():
    try:
        data = request.json
        message_data = data.get('data', {})
        
        key_info = message_data.get('key', {})
        sender_group = key_info.get('remoteJid', '')
        message_id = key_info.get('id', '')
        from_me = key_info.get('fromMe', False)
        
        if "@g.us" in sender_group and not from_me:
            is_safe, reason = check_group_message(message_data)
            
            if not is_safe:
                print(f"⚠️ مخالفة في الجروب [{sender_group}] - السبب: ({reason})! جاري مسحها...")
                delete_whatsapp_message(sender_group, message_id)
                
    except Exception as e:
        print(f"خطأ في معالجة الـ Webhook: {e}")
        
    return jsonify({"status": "received"}), 200

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)