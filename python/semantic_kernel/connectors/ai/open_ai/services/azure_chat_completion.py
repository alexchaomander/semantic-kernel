# Copyright (c) Microsoft. All rights reserved.


from logging import Logger
from typing import Dict, Optional

from semantic_kernel.connectors.ai.open_ai.services.base_chat_completions import (
    BaseChatCompletion,
)
from semantic_kernel.connectors.ai.open_ai.services.base_config_azure import (
    BaseAzureConfig,
)
from semantic_kernel.connectors.ai.open_ai.services.base_open_ai_functions import (
    OpenAIModelTypes,
)
from semantic_kernel.connectors.ai.open_ai.services.base_text_completion import (
    BaseTextCompletion,
)


class AzureChatCompletion(BaseAzureConfig, BaseChatCompletion, BaseTextCompletion):
    def __init__(
        self,
        deployment_name: str,
        endpoint: str,
        api_key: str,
        api_version: str = "2022-12-01",
        ad_auth=False,
        log: Optional[Logger] = None,
        logger: Optional[Logger] = None,
    ) -> None:
        """
        Initialize an AzureChatCompletion service.

        Arguments:
            deployment_name: The name of the Azure deployment. This value
                will correspond to the custom name you chose for your deployment
                when you deployed a model. This value can be found under
                Resource Management > Deployments in the Azure portal or, alternatively,
                under Management > Deployments in Azure OpenAI Studio.
            endpoint: The endpoint of the Azure deployment. This value
                can be found in the Keys & Endpoint section when examining
                your resource from the Azure portal.
            api_key: The API key for the Azure deployment. This value can be
                found in the Keys & Endpoint section when examining your resource in
                the Azure portal. You can use either KEY1 or KEY2.
            api_version: The API version to use. (Optional)
                The default value is "2023-03-15-preview".
            ad_auth: Whether to use Azure Active Directory authentication. (Optional)
                The default value is False.
            log: The logger instance to use. (Optional)
            logger: deprecated, use 'log' instead.
        """
        if logger:
            logger.warning("The 'logger' argument is deprecated, use 'log' instead.")
        super().__init__(
            deployment_name=deployment_name,
            endpoint=endpoint,
            api_key=api_key,
            model_type=OpenAIModelTypes.CHAT,
            api_version=api_version,
            log=log or logger,
            ad_auth=ad_auth,
        )

    @classmethod
    def from_dict(cls, settings: Dict[str, str]) -> "AzureChatCompletion":
        """
        Initialize an Azure OpenAI service from a dictionary of settings.

        Arguments:
            settings: A dictionary of settings for the service.
                should contains keys: deployment_name, endpoint, api_key
                and optionally: api_version, ad_auth, log
        """
        if "api_type" in settings:
            settings["ad_auth"] = settings["api_type"] == "azure_ad"
            del settings["api_type"]

        return AzureChatCompletion(
            deployment_name=settings["deployment_name"],
            endpoint=settings["endpoint"],
            api_key=settings["api_key"],
            api_version=settings.get("api_version"),
            ad_auth=settings.get("ad_auth", False),
            log=settings.get("log"),
        )
