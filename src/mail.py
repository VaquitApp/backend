from abc import ABC, abstractmethod
import os
from logging import info, error, warning
import sib_api_v3_sdk as sdk
from sib_api_v3_sdk.rest import ApiException

from src import schemas

API_KEY = os.environ.get("EMAIL_API_KEY")
TEMPLATE_ID = 1


class MailSender(ABC):
    @abstractmethod
    def send(self, sender: str, receiver: str, group_name: str) -> bool:
        pass


class ProdMailSender(MailSender):
    def send(
        self, sender: str, receiver: str, group: schemas.Group, token: str
    ) -> bool:
        configuration = sdk.Configuration()
        configuration.api_key["api-key"] = API_KEY

        api_instance = sdk.TransactionalEmailsApi(sdk.ApiClient(configuration))

        to = [{"email": receiver}]
        params = {
            "sender": sender,
            "group_name": group.name,
            "group_description": group.description,
            "token": token,
        }

        email = sdk.SendSmtpEmail(to=to, template_id=TEMPLATE_ID, params=params)

        try:
            response = api_instance.send_transac_email(email)
            info(response)
            return True
        except ApiException as e:
            error(f"Failed to send email with error: {e}")
            return False


class LocalMailSender(MailSender):
    def send(
        self, sender: str, receiver: str, group: schemas.Group, token: str
    ) -> bool:
        return True


if API_KEY is not None:
    mail_service = ProdMailSender()
else:
    warning("MailSender API Key not detected, defaulting to NO-OP Service.")
    mail_service = LocalMailSender()
