import email
import imaplib

EMAIL = 'arnoldnderitu@gmail.com'
PASSWORD = 'P3rf3ct10n!2021'
SERVER = 'imap.gmail.com'


# connect to the server and go to its inbox
mail = imaplib.IMAP4_SSL(SERVER)
mail.login(EMAIL, PASSWORD)

# choose the inbox but you can can select others
mail.select('inbox')

# we'll search using the ALL criteria to retrieve every message inside the inbox
# it will return with its status and a list of ids
status, data = mail.search(None, 'ALL')

# the list returned is a list of bytes separated 
mail_ids = []

# go through the list splitting its blocks of bytes and appending to the mail_ids list
for block in data:
    # transforms the text or bytes into a list white spaces as separator
    # b'1 2 3.split() => [b'1', b'2', b'3']
    mail_ids += block.split()

# for every id fetch the email to extract its content
for i in mail_ids:
    # fetch the email given its id and format that you want the message to be 
    status, data = mail.fetch(i, '(RFC822)')

    # the content data at the '(RFC822)' format comes on 
    # a list with a tuple with header, content, and the closing
    # byte b')'
    for response_part in data:
        # so if its a tuple
        if isinstance(response_part, tuple):
            # we for the content at its second element
            # skipping the header at the first and the closing
            # at the third
            message = email.message_from_bytes(response_part[1])

            # with the content we can extract the info about 
            # who sent the message and its subject 
            mail_from = message['from']
            mail_subject = message['subject']

            # then for the text, which can be in plaintext or mutlipart
            if message.is_multipart():
                mail_content = ''

                for part in message.get_payload():
                    if part.get_content_type() == 'text/plain':
                        mail_content += part.get_payload()
            else:
                mail_content = message.get_payload()

            print("From: "+ mail_from)
            print("Subject: "+ str(mail_subject))
            print("Content: "+ mail_content)







            

