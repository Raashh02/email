
import imaplib, email, numpy as np, faiss
from sentence_transformers import SentenceTransformer
from email import message_from_bytes
from email.header import decode_header
print(" Loading model...")
model = SentenceTransformer("all-mpnet-base-v2")
print("Model loaded.")
def extract_body(msg_obj):
    if msg_obj.is_multipart():
        for part in msg_obj.walk():
            if part.get_content_type() == "text/plain":
                try:
                    return part.get_payload(decode=True).decode(errors="ignore")
                except:
                    continue
    else:
        try:
            return msg_obj.get_payload(decode=True).decode(errors="ignore")
        except:
            pass
    return ""
user_email = input("Enter your Gmail address: ")
app_password = input(" Enter your Gmail App Password (16 characters): ")
print("\n Optional Filters (Press Enter to skip):")
from_filter = input(" Sender email (e.g., irctc@alerts.com): ").strip()
after_date = input(" After date (e.g., 01-Jul-2024): ").strip()
before_date = input(" Before date (e.g., 10-Jul-2024): ").strip()
search_query = []
if from_filter:
    search_query += ["FROM", f'"{from_filter}"']
if after_date:
    search_query += ["SINCE", after_date]
if before_date:
    search_query += ["BEFORE", before_date]
if not search_query:
    search_query = ["ALL"]
imap = imaplib.IMAP4_SSL("imap.gmail.com")
imap.login(user_email, app_password)
imap.select("inbox")
_, data = imap.search(None, *search_query)
email_ids = data[0].split()

if not email_ids:
    print(" No emails found with your filters.")
    imap.logout()
else:
    print(f"\n Found {len(email_ids)} emails. Processing up to 20 latest...\n")
    emails = []
    raw_texts = []

    email_ids = email_ids[-20:]  
    for eid in reversed(email_ids):
        _, msg_data = imap.fetch(eid, "(RFC822)")
        for part in msg_data:
            if isinstance(part, tuple):
                msg_obj = message_from_bytes(part[1])
                subject, _ = decode_header(msg_obj.get("Subject", ""))[0]
                if isinstance(subject, bytes): subject = subject.decode("utf-8", "ignore")
                sender = msg_obj.get("From", "")
                date = msg_obj.get("Date", "")
                body = extract_body(msg_obj)
                combined = f"{subject}\n{body}".strip()

                emails.append({
                    "subject": subject,
                    "from": sender,
                    "date": date,
                    "preview": body[:300],
                    "full": combined
                })
                raw_texts.append(combined)

    print(f"\n {len(emails)} emails loaded. Encoding vectors...\n")
    vectors = model.encode(raw_texts, convert_to_numpy=True)
    print(f" Embedding shape: {vectors.shape}")
    index = faiss.IndexFlatL2(vectors.shape[1])
    index.add(vectors)
    query = input(" Enter your search query: ").strip()
    query_vec = model.encode([query], convert_to_numpy=True)
    _, top_indices = index.search(query_vec, k=5)
    print(f"\n Top 5 matches for: '{query}'\n" + "="*60)
    for i in top_indices[0]:
        mail = emails[i]
        print(f"\n Subject: {mail['subject']}")
        print(f" From   : {mail['from']}")
        print(f"Date   : {mail['date']}")
        print(f"Preview:\n{mail['preview']}...")
        print("-" * 60)

    imap.logout()
