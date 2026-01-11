import random

from otree.api import (
    models,
    widgets,
    BaseConstants,
    BaseSubsession,
    BaseGroup,
    BasePlayer,
)

doc = """
Your app description
"""


class Constants(BaseConstants):
    name_in_url = 'wiki'
    players_per_group = None
    num_rounds = 1


class Subsession(BaseSubsession):
    def creating_session(self):
        for p in self.get_players():
            # Random group assignment for which article version to show
            assignment = random.randint(0, 2)
            p.group_assignment = assignment

            treatments = {
                0: 'Control',
                1: 'Treatment_A',
                2: 'Treatment_B',
            }
            p.treatment = treatments[assignment]


class Group(BaseGroup):
    pass


class Player(BasePlayer):
    group_assignment = models.IntegerField()
    treatment = models.StringField()

    # Reading behavior tracking
    max_scroll_depth = models.FloatField(initial=0)  # Percentage 0-100
    tab_switches = models.IntegerField(initial=0)  # Number of times they left the tab
    link_click_attempts = models.IntegerField(initial=0)  # Times they tried to click disabled links
    reading_time_seconds = models.IntegerField(initial=0)  # Time spent on Wikipedia page

    # Before questions (knowledge assessment)
    before_q1 = models.IntegerField(
        label="How familiar are you with this topic?",
        choices=[1, 2, 3, 4, 5],
        widget=widgets.RadioSelect
    )
    before_q2 = models.IntegerField(
        label="How confident are you in your knowledge?",
        choices=[1, 2, 3, 4, 5],
        widget=widgets.RadioSelect
    )
    before_q3 = models.StringField(
        label="Write what you know about this topic (in a few sentences)",
        blank=True
    )

    # After questions (knowledge assessment + evaluation)
    after_q1 = models.IntegerField(
        label="How familiar are you with this topic now?",
        choices=[1, 2, 3, 4, 5],
        widget=widgets.RadioSelect
    )
    after_q2 = models.IntegerField(
        label="How confident are you in your knowledge now?",
        choices=[1, 2, 3, 4, 5],
        widget=widgets.RadioSelect
    )
    after_q3 = models.StringField(
        label="Write what you now know about this topic (in a few sentences)",
        blank=True
    )
    after_q4 = models.IntegerField(
        label="How credible did you find the Wikipedia article?",
        choices=[1, 2, 3, 4, 5],
        widget=widgets.RadioSelect
    )
    after_q5 = models.IntegerField(
        label="Did the article change your perspective?",
        choices=[
            [1, "Not at all"],
            [2, "Slightly"],
            [3, "Moderately"],
            [4, "Significantly"],
            [5, "Completely"],
        ],
        widget=widgets.RadioSelect
    )
