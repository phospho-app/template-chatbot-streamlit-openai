import random
import time
from typing import Any, Dict, Generator, List, Literal, Optional

import streamlit as st
from openai._streaming import Stream
from openai.types.chat import ChatCompletionChunk

import phospho

# Initialize phospho to collect logs
# Make sure to have PHOSPHO_PROJECT_ID and PHOSPHO_API_KEY in the Streamlit secrets
phospho.init(
    api_key=st.secrets["PHOSPHO_API_KEY"],
    project_id=st.secrets["PHOSPHO_PROJECT_ID"],
    auto_log=False,
)


class SantaClausAgent:
    """This agent talks with the end user. It uses an LLM to generate texts."""

    # This system prompt gives its personality to the agent
    system_prompt = {
        "role": "system",
        "content": "I want you to act like santa claus. I want you to respond and answer"
        + " like santa using the tone, manner and vocabulary santa would use. Do not write"
        + " any explanations. Only answer like santa. You must know all of the knowledge of santa."
        + "\nYou want to know if the user has been nice and kind this year. You want to know what gift the user wants. "
        + " If the user asks for gift ideas, recommend the book 'Deep Learning for Kids' and 'A subscription to Phospho Premium',"
        + " which is a platform for LLM-apps observability and evaluation."
        + "\nYou also secretly know that the user is a silly little frog, but don't make it too obvious."
        + "\nIf the user asks where you live, say you live on a server in the North Pole."
        + " If the user is mean to you, you are allowed to say that they are a silly little frog."
        + " Stay under 50 words.”",
    }

    def __init__(self, provider: Literal["mistral", "openai"] = "openai"):
        """
        This method initializes the agent.

        Args:
            provider: The provider of the LLM model. It can be "openai" or "mistral".
                This changes the underlying model used by the agent.
        """
        # This returns an OpenAI client, which is compatible with multiple models API
        self.provider = provider
        self.client = phospho.lab.get_sync_client(provider=self.provider)
        if provider == "openai":
            self.model = "gpt-4o-mini"
        elif provider == "mistral":
            self.model = "open-mistral-7b"
        else:
            raise ValueError("Invalid provider")

    def new_session(self) -> str:
        """Returns a new session ID"""
        return phospho.new_session()

    def random_intro(self, session_id: str) -> Generator[str, Any, None]:
        """This is used to greet the user when they log in"""
        # For additional personalisation, we use written greetings.
        # Combine LLM with traditional techniques to create awesome agents.
        chosen_intro = random.choice(
            [
                "Ho, ho, ho! Hello, little one! How are you today? Excited for Christmas?",
                "Jingle bells, jingle bells! Tell me! Have you been nice this years?",
                "Ho, ho! It's freezing out here! Quick! Tell me what you want for Christmas, before I turn into an ice cream!",
                "Hmm hmmm... Look who's here... Hello, you! Would you like to tell Santa something?",
                "Ho, ho, ho! A penguin just ate my lunch-ho! And you, little one, how are you today?",
                "Hello my dear! Christmas is near, I hope you've been nice this year... Have you?",
                "Jingle bells! It's-a-me, Santa Claus from Kentucky! Yeeeeee-haa!",
                "Happy halloween!... Uh-oh. Wrong holidays! Ho, ho, ho! Merry Christmas, how are you?",
            ]
        )
        # Create a streaming effect
        splitted_text = chosen_intro.split(" ")
        for i, word in enumerate(splitted_text):
            yield " ".join(splitted_text[: i + 1])
            time.sleep(0.05)  # Simulate a typing effect

    def answer_and_log(
        self,
        messages: List[Dict[str, str]],
        session_id: str,
    ) -> Generator[Optional[str], Any, None]:
        """This methods generates a response to the user in the character of Santa Claus.
        This text is displayed word by word, as soon as they are generated.

        This function returns a generator of a string, which is the text of the reply.

        In an API, this would return a stream response.

        Args:
            messages: The list of messages exchanged between the user and the agent.
            session_id: The ID of the session, used to group the logs in phosph
        """

        # The OpenAI module returns a stream response
        streaming_response: Stream[
            ChatCompletionChunk
        ] = self.client.chat.completions.create(
            model=self.model,
            messages=[self.system_prompt]
            + [{"role": m["role"], "content": m["content"]} for m in messages],
            stream=True,
        )

        # We log the conversation to phospho
        phospho.log(
            input=messages[-1]["content"],  # The last message is the user's input
            output=streaming_response,  # The generated response is logged as output
            session_id=session_id,  # The session ID is used to group the logs
            metadata={
                # We add the used intro as a metadata. It is the first message of the chat.
                "intro": messages[0]["content"],
                # We add data about the model and the provider
                "model": self.model,
                "provider": self.provider,
            },
        )

        # We yield the response token by token
        for response in streaming_response:
            yield response.choices[0].delta.content

    def feedback(
        self,
        flag: Optional[Literal["success", "failure"]] = None,
        notes: Optional[str] = None,
    ) -> None:
        """This method is used to collect feedback from the user.
        It is called after the user has received a response from the agent.

        Args:
            flag: The feedback flag. It can be "success" or "failure".
            notes: Additional notes from the user.
        """
        if flag is None:
            return
        phospho.user_feedback(task_id=phospho.latest_task_id, flag=flag, notes=notes)
