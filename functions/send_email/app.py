import os
import boto3

SEND_EMAIL = os.environ['SEND_EMAIL']
EMAIL_SENDER = os.environ['EMAIL_SENDER']
EMAIL_CC = os.environ['EMAIL_CC'].split(',')
EMAIL_BCC = os.environ['EMAIL_BCC'].split(',')
EMAIL_RETURN_PATH = os.environ['EMAIL_RETURN_PATH']

client = boto3.client('ses')


def lambda_handler(data, _context):

    print(data)

    if SEND_EMAIL == 'No':
        print("Email disabled.")
        return data

    print('EMAIL_SENDER: ', EMAIL_SENDER)
    print('EMAIL_CC: ', EMAIL_CC)
    print('EMAIL_BCC: ', EMAIL_BCC)
    print('EMAIL_RETURN_PATH: ', EMAIL_RETURN_PATH)

    recipients = data['Recipient']
    print("Recipients: ", recipients)

    subject = data['Subject']
    if len(subject) > 100:
        subject = subject[:97] + '...'
    body = data['Body']
    fmt = 'Html' if data.get('Html') else 'Text'
    ticket_id = data.get('TicketId', False)

    if ticket_id:
        body = body.replace('- - -', f"Ticket ID: {ticket_id}", 1)

    for recipient in recipients.split(','):
        destination = {
            'ToAddresses': [
                recipient
            ]
        }
        if EMAIL_CC != ['']:
            destination['CcAddresses'] = EMAIL_CC
        if EMAIL_BCC != ['']:
            destination['BccAddresses'] = EMAIL_BCC

        response = client.send_email(
            Source=EMAIL_SENDER,
            Destination=destination,
            Message={
                'Subject': {
                    'Charset': 'UTF-8',
                    'Data': subject
                },
                'Body': {
                    fmt: {
                        'Charset': 'UTF-8',
                        'Data': body
                    }
                }
            },
            ReplyToAddresses=[],
            ReturnPath=EMAIL_RETURN_PATH
        )
        print(response)

    return data
