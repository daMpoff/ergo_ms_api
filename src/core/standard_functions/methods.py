from django.core.mail import send_mail

def parse_errors_to_dict(error_dict):
    parsed_errors = {}
    for field, details in error_dict.items():
        parsed_errors[field] = ", ".join(str(detail) for detail in details)
    return parsed_errors

def send_confirmation_email(email, code):
    subject = "Код подтверждения ERGO MS"
    message = f"Ваш код подтверждения: {code}"
    from_email = "muzalevskij.evgenij@mail.ru"
    recipient_list = [email]

    send_mail(subject,
              message, 
              from_email, 
              recipient_list, 
              fail_silently=False)