from enum import Enum


class ClientMsgTypes(Enum):
    """
    Used to specify the type of message to send to the client.
    Status messages are displayed in the status bar,
    while notifications are displayed as a popup.
    """

    STATUS = "status"
    NOTIFICATION = "notification"
    BOTH = "both"

    def __eq__(self, other):
        return self.value == other.value
