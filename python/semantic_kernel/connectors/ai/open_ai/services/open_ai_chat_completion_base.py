# Copyright (c) Microsoft. All rights reserved.

from logging import Logger
from typing import Any, List, Optional, Tuple, Union

import openai
from pydantic import constr

from semantic_kernel.connectors.ai.ai_exception import AIException
from semantic_kernel.connectors.ai.chat_completion_client_base import (
    ChatCompletionClientBase,
)
from semantic_kernel.connectors.ai.chat_request_settings import ChatRequestSettings
from semantic_kernel.connectors.ai.complete_request_settings import (
    CompleteRequestSettings,
)
from semantic_kernel.connectors.ai.text_completion_client_base import (
    TextCompletionClientBase,
)
from semantic_kernel.sk_pydantic import HttpsUrl


class OpenAIChatCompletionBase(ChatCompletionClientBase, TextCompletionClientBase):
    model_id: constr(strip_whitespace=True, min_length=1)
    api_key: constr(strip_whitespace=True, min_length=1)
    api_type: str
    org_id: Optional[str] = None
    api_version: Optional[str] = None
    endpoint: Optional[HttpsUrl] = None

    async def complete_chat_async(
        self,
        messages: List[Tuple[str, str]],
        request_settings: ChatRequestSettings,
        logger: Optional[Logger] = None,
    ) -> Union[str, List[str]]:
        response = await self._send_chat_request(messages, request_settings, False)

        if len(response.choices) == 1:
            return response.choices[0].message.content
        else:
            return [choice.message.content for choice in response.choices]

    async def complete_chat_stream_async(
        self,
        messages: List[Tuple[str, str]],
        request_settings: ChatRequestSettings,
        logger: Optional[Logger] = None,
    ):
        response = await self._send_chat_request(messages, request_settings, True)

        # parse the completion text(s) and yield them
        async for chunk in response:
            text, index = _parse_choices(chunk)
            # if multiple responses are requested, keep track of them
            if request_settings.number_of_responses > 1:
                completions = [""] * request_settings.number_of_responses
                completions[index] = text
                yield completions
            # if only one response is requested, yield it
            else:
                yield text

    async def complete_async(
        self,
        prompt: str,
        request_settings: CompleteRequestSettings,
        logger: Optional[Logger] = None,
    ) -> Union[str, List[str]]:
        """
        Completes the given prompt.

        Arguments:
            prompt {str} -- The prompt to complete.
            request_settings {CompleteRequestSettings} -- The request settings.

        Returns:
            str -- The completed text.
        """
        prompt_to_message = [("user", prompt)]
        chat_settings = ChatRequestSettings.from_completion_config(request_settings)

        response = await self._send_chat_request(
            prompt_to_message, chat_settings, False
        )

        if len(response.choices) == 1:
            return response.choices[0].message.content
        else:
            return [choice.message.content for choice in response.choices]

    async def complete_stream_async(
        self,
        prompt: str,
        request_settings: CompleteRequestSettings,
        logger: Optional[Logger] = None,
    ):
        prompt_to_message = [("user", prompt)]
        chat_settings = ChatRequestSettings(
            temperature=request_settings.temperature,
            top_p=request_settings.top_p,
            presence_penalty=request_settings.presence_penalty,
            frequency_penalty=request_settings.frequency_penalty,
            max_tokens=request_settings.max_tokens,
            number_of_responses=request_settings.number_of_responses,
            token_selection_biases=request_settings.token_selection_biases,
            stop_sequences=request_settings.stop_sequences,
        )
        response = await self._send_chat_request(prompt_to_message, chat_settings, True)

        # parse the completion text(s) and yield them
        async for chunk in response:
            text, index = _parse_choices(chunk)
            # if multiple responses are requested, keep track of them
            if request_settings.number_of_responses > 1:
                completions = [""] * request_settings.number_of_responses
                completions[index] = text
                yield completions
            # if only one response is requested, yield it
            else:
                yield text

    async def _send_chat_request(
        self,
        messages: List[Tuple[str, str]],
        request_settings: ChatRequestSettings,
        stream: bool,
    ):
        """
        Completes the given user message with an asynchronous stream.

        Arguments:
            user_message {str} -- The message (from a user) to respond to.
            request_settings {ChatRequestSettings} -- The request settings.

        Returns:
            str -- The completed text.
        """
        if request_settings is None:
            raise ValueError("The request settings cannot be `None`")

        if request_settings.max_tokens < 1:
            raise AIException(
                AIException.ErrorCodes.InvalidRequest,
                "The max tokens must be greater than 0, "
                f"but was {request_settings.max_tokens}",
            )

        if len(messages) <= 0:
            raise AIException(
                AIException.ErrorCodes.InvalidRequest,
                "To complete a chat you need at least one message",
            )

        if messages[-1][0] != "user":
            raise AIException(
                AIException.ErrorCodes.InvalidRequest,
                "The last message must be from the user",
            )

        model_args = {}
        if self.api_type in ["azure", "azure_ad"]:
            model_args["engine"] = self.model_id
        else:
            model_args["model"] = self.model_id

        formatted_messages = [
            {"role": role, "content": message} for role, message in messages
        ]

        try:
            response: Any = await openai.ChatCompletion.acreate(
                **model_args,
                api_key=self.api_key,
                api_type=self.api_type,
                api_base=self.endpoint,
                api_version=self.api_version,
                organization=self.org_id,
                messages=formatted_messages,
                temperature=request_settings.temperature,
                top_p=request_settings.top_p,
                n=request_settings.number_of_responses,
                stream=stream,
                stop=(
                    request_settings.stop_sequences
                    if request_settings.stop_sequences is not None
                    and len(request_settings.stop_sequences) > 0
                    else None
                ),
                max_tokens=request_settings.max_tokens,
                presence_penalty=request_settings.presence_penalty,
                frequency_penalty=request_settings.frequency_penalty,
                logit_bias=(
                    request_settings.token_selection_biases
                    if request_settings.token_selection_biases is not None
                    and len(request_settings.token_selection_biases) > 0
                    else {}
                ),
            )
        except Exception as ex:
            raise AIException(
                AIException.ErrorCodes.ServiceError,
                "OpenAI service failed to complete the chat",
                ex,
            )

        if "usage" in response:
            self.capture_usage_details(**response.usage)

        return response


def _parse_choices(chunk):
    message = ""
    if "role" in chunk.choices[0].delta:
        message += chunk.choices[0].delta.role + ": "
    if "content" in chunk.choices[0].delta:
        message += chunk.choices[0].delta.content

    index = chunk.choices[0].index
    return message, index