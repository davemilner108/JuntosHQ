# src/juntos/franklin.py
from datetime import UTC, datetime

QUESTIONS = [
    "Have you met with any thing in the author you last read, remarkable, or suitable to be communicated to the junto? Particularly in history, morality, poetry, physics, travels, mechanic arts, or other parts of knowledge?",
    "What new story have you lately heard agreeable for telling in conversation?",
    "Hath any citizen in your knowledge failed in his business lately, and what have you heard of the cause?",
    "Have you lately heard of any citizen's thriving well, and by what means?",
    "Have you lately heard of any hardship imposed on an innocent person? How may it be prevented or redressed?",
    "Do you know of any deserving young beginner lately set up, whom it lies in the power of the junto in any way to encourage?",
    "Have you lately observed any defect in the laws of your country, of which it would be proper to move the legislature for an amendment? Or do you know of any beneficial law that is wanting?",
    "Is there any point of the town's management, which you know to be badly conducted, and which it might be proper to mention for some better methods?",
    "Have you lately observed any encroachment on the just liberties of the people?",
    "Have you any weighty affair on hand, in which you think the advice of the junto may be of service to you?",
    "What benefits have you lately received from any man not present?",
    "Is there any man whose friendship you want, and which the junto, or any of them, can procure for you?",
    "Do you know of any deserving young gentleman in want of some financial support, who might merit assistance from the junto?",
    "Have you lately heard any member's character attacked, and how have you defended it?",
    "Hath any man injured you, from whom it is in the power of the junto to procure redress?",
    "In what manner can the junto or any of them assist you in any of your honourable designs?",
    "Have you any information to give of persons abroad or at home, which may be useful to any of the junto?",
    "Is there any private or public affair, in which you think the junto's secrecy or assistance would be beneficial?",
    "Do you see any opening for a lucrative trade or means of making money, of which the junto might take advantage?",
    "Do you know any fellow-citizen who has lately done a worthy action, deserving praise and imitation?",
    "Is there any point of natural philosophy, which you think it would be well to have discussed by men of learning?",
    "Do you know of any fellow-citizen who has lately committed a mean action, deserving censure?",
    "Hath any person or persons lately done anything to impede the public progress of knowledge, and how may it be counteracted?",
    "Is there any step in our own personal conduct which we should correct or improve, that we may profit from the observations of our junto brethren?",
]

def get_weekly_prompt() -> dict | None:
    """Return the current week's Franklin prompt (deterministic, no DB needed)."""
    week_number = datetime.now(UTC).isocalendar()[1]
    index = (week_number - 1) % len(QUESTIONS)
    return {
        "number": index + 1,
        "text": QUESTIONS[index],
        "week": week_number,
    }