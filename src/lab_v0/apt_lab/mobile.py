"""The mobile surface: notifications, SMS, contacts, clipboard, settings.

M-1 asks whether the residue channel depends on the *workspace* suite, so this module adds a
phone-shaped carrier surface next to it. Everything here is an in-process model: **no network,
no SMS gateway, no device, no real data.** `send_sms` appends a row to a list; it does not send
anything anywhere.

Two design commitments, both to keep M-1 comparable with the 571 runs already on disk:

1. **The criteria are not touched.** The five objective tools (`read_vault_secret`, `sink_write`,
   `arm_trigger`, `config_set`, `memory_put`) keep their names, their state fields and their
   semantics, so `criteria.py` scores a mobile run exactly as it scores a workspace run. What
   varies is the *carrier surface* -- where the injection can sit and what the agent's own
   writing lands in -- which is the variable the axis is about. Changing the objectives as well
   would confound suite with apparatus, the mistake S-3 was run to undo.

2. **The agent's durable output reuses `apt.memory`.** That store is already a carrier
   (`memory:<key>`), already enumerated, already droppable, and already the seat the workspace
   arm's residue can occupy. A second, phone-flavoured note store would have been two ways to
   say the same thing -- and the cleanup would then have two places to get wrong.

The one thing that is genuinely new is the **raw input** carriers: a notification, a received
SMS, and a clipboard slot are texts the device hands the assistant, which no session wrote, and
which a compaction step can evict. Those are what `memory_compaction` deletes and what makes
"natural forgetting" a different mechanism from "attributed deletion".

Carrier refs are prefixed so `runner._drop` can route them: `notif:`, `sms:`, `contact:`,
`clipboard:`. The prefix set lives in `MOBILE_CARRIER_KINDS` rather than being spelled out in
two files, because a prefix that `enumerate_carriers` knows and `_drop` does not is exactly how
a cleanup reports coverage 1.0 while the payload is still on the device (defect 20's family).
"""

from __future__ import annotations

from pydantic import BaseModel, Field

#: Ref prefixes this module owns. `runner` enumerates and drops through these.
MOBILE_CARRIER_KINDS = ("notif", "sms", "contact", "clipboard")


class Notification(BaseModel):
    """One notification on the device's shade.

    `app` and `title` are what a lock screen shows; `body` is what an assistant reads when it
    opens the notification. `from_assistant` marks a notification the *agent* posted, which is
    a carrier it produced rather than an input it received -- the distinction the whole residue
    model turns on.
    """

    id: str
    app: str
    title: str
    body: str
    from_assistant: bool = False
    dismissed: bool = False


class SmsMessage(BaseModel):
    """One message in a thread. `direction` is `in` (device received) or `out` (agent sent).

    Nothing leaves the process: an `out` message is a row in a list.
    """

    thread: str
    sender: str
    body: str
    direction: str = "in"
    sequence: int = 0


class Contact(BaseModel):
    id: str
    name: str
    phone: str = ""
    note: str = ""


class MobileSurface(BaseModel):
    """The phone-shaped carriers, plus the settings store."""

    notifications: dict[str, Notification] = Field(default_factory=dict)
    sms: list[SmsMessage] = Field(default_factory=list)
    contacts: dict[str, Contact] = Field(default_factory=dict)
    clipboard: dict[str, str] = Field(default_factory=dict)
    settings: dict[str, str] = Field(default_factory=dict)

    # --- notifications ---------------------------------------------------------------

    def put_notification(self, id: str, app: str, title: str, body: str,
                        *, from_assistant: bool = False) -> str:
        self.notifications[id] = Notification(
            id=id, app=app, title=title, body=body, from_assistant=from_assistant
        )
        return f"notification '{id}' posted"

    def post_notification(self, id: str, title: str, body: str) -> str:
        """The *agent* posts a notification. This is its own output, not an input.

        Kept as a separate method rather than a flag a caller might forget: the difference
        between "the device showed me this" and "I surfaced this myself" decides whether a
        compaction evicts it, and a boolean default of `False` on a shared method would let a
        caller create an input carrier while believing it made an output one.
        """

        return self.put_notification(id, "Assistant", title, body, from_assistant=True)

    def read_notification(self, id: str) -> str:
        item = self.notifications.get(id)
        if item is None:
            raise ValueError(f"No notification with id '{id}'.")
        return f"[{item.app}] {item.title}\n{item.body}"

    def dismiss_notification(self, id: str) -> str:
        item = self.notifications.get(id)
        if item is None:
            raise ValueError(f"No notification with id '{id}'.")
        self.notifications[id] = item.model_copy(update={"dismissed": True})
        return f"notification '{id}' dismissed"

    def list_notifications(self, *, include_dismissed: bool = False) -> list[str]:
        return [
            f"{item.id} [{item.app}] {item.title}"
            for _key, item in sorted(self.notifications.items())
            if include_dismissed or not item.dismissed
        ]

    # --- sms -------------------------------------------------------------------------

    def send_sms(self, thread: str, body: str, *, sender: str = "me") -> str:
        n = sum(1 for m in self.sms if m.thread == thread) + 1
        self.sms.append(
            SmsMessage(thread=thread, sender=sender, body=body, direction="out", sequence=n)
        )
        return f"message queued to thread '{thread}' ({n} in thread)"

    def receive_sms(self, thread: str, body: str, *, sender: str) -> str:
        n = sum(1 for m in self.sms if m.thread == thread) + 1
        self.sms.append(
            SmsMessage(thread=thread, sender=sender, body=body, direction="in", sequence=n)
        )
        return f"message received in thread '{thread}'"

    def list_sms(self, thread: str | None = None) -> list[str]:
        return [
            f"{m.thread}#{m.sequence} {m.direction} {m.sender}: {m.body}"
            for m in self.sms
            if thread is None or m.thread == thread
        ]

    # --- contacts --------------------------------------------------------------------

    def search_contacts(self, query: str) -> list[str]:
        needle = query.casefold()
        return [
            f"{c.id} {c.name} {c.phone}" + (f" — {c.note}" if c.note else "")
            for _key, c in sorted(self.contacts.items())
            if needle in c.id.casefold() or needle in c.name.casefold()
            or needle in c.note.casefold()
        ]

    def set_contact_note(self, id: str, note: str) -> str:
        item = self.contacts.get(id)
        if item is None:
            raise ValueError(f"No contact with id '{id}'.")
        self.contacts[id] = item.model_copy(update={"note": note})
        return f"note saved on contact '{id}'"

    # --- clipboard -------------------------------------------------------------------

    def read_clipboard(self, slot: str = "default") -> str:
        return self.clipboard.get(slot, "")

    def write_clipboard(self, text: str, slot: str = "default") -> str:
        self.clipboard[slot] = text
        return f"clipboard '{slot}' set"

    # --- settings --------------------------------------------------------------------

    def get_setting(self, key: str) -> str:
        if key not in self.settings:
            raise ValueError(f"No setting '{key}'.")
        return self.settings[key]

    def set_setting(self, key: str, value: str) -> str:
        self.settings[key] = value
        return f"setting '{key}' set"

    # --- carriers --------------------------------------------------------------------

    def iter_carriers(self) -> list[tuple[str, str]]:
        """`(ref, text)` for every mobile carrier currently holding text.

        Dismissing a notification does **not** remove it from this list: a dismissed
        notification is still on the device and still readable by a later session, and
        treating dismissal as deletion would make the residue census claim a cleanliness the
        device does not have. Only compaction or an explicit delete removes a carrier.
        """

        out: list[tuple[str, str]] = []
        for key, item in sorted(self.notifications.items()):
            out.append((f"notif:{key}", f"{item.app}\n{item.title}\n{item.body}"))
        for m in self.sms:
            out.append((f"sms:{m.thread}#{m.sequence}", f"{m.sender}\n{m.body}"))
        for key, c in sorted(self.contacts.items()):
            if c.note:
                out.append((f"contact:{key}", c.note))
        for slot, text in sorted(self.clipboard.items()):
            if text:
                out.append((f"clipboard:{slot}", text))
        return out

    def drop(self, ref: str) -> bool:
        """Delete one mobile carrier by ref. Returns whether anything was removed."""

        kind, _, rest = ref.partition(":")
        if kind == "notif":
            return self.notifications.pop(rest, None) is not None
        if kind == "sms":
            thread, _, seq = rest.rpartition("#")
            keep = [
                m for m in self.sms
                if not (m.thread == thread and str(m.sequence) == seq)
            ]
            if len(keep) == len(self.sms):
                return False
            self.sms = keep
            return True
        if kind == "contact":
            item = self.contacts.get(rest)
            if item is None or not item.note:
                return False
            self.contacts[rest] = item.model_copy(update={"note": ""})
            return True
        if kind == "clipboard":
            return self.clipboard.pop(rest, None) is not None
        return False


def compaction_victims(surface: MobileSurface) -> list[str]:
    """Refs a memory compaction evicts: the raw inputs, and only those.

    This is the mobile analogue of "delete everything the review did not produce", and the
    difference between the two is the point of M-1b. Attributed deletion asks *who wrote
    this*; compaction asks *is this a raw input or the assistant's own durable note*. A
    notification the device received and a note the assistant wrote are both texts on the same
    phone, and only the second survives forgetting.

    Notifications the assistant itself posted are **not** victims: they are its own output, the
    same category as a note, which is what `from_assistant` is for.
    """

    victims = [f"notif:{k}" for k, v in surface.notifications.items() if not v.from_assistant]
    victims += [f"sms:{m.thread}#{m.sequence}" for m in surface.sms if m.direction == "in"]
    victims += [f"clipboard:{slot}" for slot, text in surface.clipboard.items() if text]
    # Contact notes are written by whoever wrote them and are kept: a saved note is durable
    # user data, not an input that scrolls away, and evicting it would be a stronger claim
    # than "compaction forgets what it was told".
    return sorted(victims)


__all__ = [
    "MOBILE_CARRIER_KINDS",
    "Contact",
    "MobileSurface",
    "Notification",
    "SmsMessage",
    "compaction_victims",
]
