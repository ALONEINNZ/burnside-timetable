import base64
from email.mime.text import MIMEText


def create_email(sender, to, subject, content):
    email = MIMEText(content)
    email["to"] = to
    email["sender"] = sender
    email["subject"] = subject
    rawemail = base64.urlsafe_b64encode(email.as_string().encode("utf-8"))
    return {"raw": rawemail.decode("utf-8")}


def create_draft(service, user_id, message_body):
    try:
        message = {"message": message_body}
        draft = service.users().drafts().create(userId=user_id, body=message).execute()
        print("Draft id: %s\nDraft message: %s" % (draft["id"], draft["message"]))
        return draft
    except Exception as e:
        print("An error occurred: %s" % e)
        return None


def send_message(service, user_id, message):
    try:
        message = (
            service.users().messages().send(userId=user_id, body=message).execute()
        )
        print("Message Id: %s" % message["id"])
        return message
    except Exception as e:
        print("An error occurred: %s" % e)
        return None
