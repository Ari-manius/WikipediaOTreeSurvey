from ._builtin import Page
from .models import Player


class BeforeQuestions(Page):
    """Before viewing the Wikipedia article - baseline knowledge assessment"""
    form_model = Player
    form_fields = ['before_q1', 'before_q2', 'before_q3']


class WikipediaDisplay(Page):
    """Display the fake Wikipedia article"""
    form_model = Player
    form_fields = ['max_scroll_depth', 'tab_switches', 'link_click_attempts', 'reading_time_seconds']
    timeout_seconds = 300  # 5 minute timeout to read article

    def vars_for_template(self):
        articles = {
            0: 'nanjing_massacre.html',
            1: 'nanjing_massacre.html',  # Can change to different article
            2: 'nanjing_massacre.html',
        }
        return dict(
            wiki_article_url=articles.get(self.player.group_assignment, 'nanjing_massacre.html')
        )


class AfterQuestions(Page):
    """After viewing the Wikipedia article - knowledge assessment + article evaluation"""
    form_model = Player
    form_fields = ['after_q1', 'after_q2', 'after_q3', 'after_q4', 'after_q5']


class Results(Page):
    """Show comparison of before/after responses"""

    def vars_for_template(self):
        familiarity_change = self.player.after_q1 - self.player.before_q1
        confidence_change = self.player.after_q2 - self.player.before_q2

        return dict(
            familiarity_change=familiarity_change,
            familiarity_change_abs=abs(familiarity_change),
            confidence_change=confidence_change,
            confidence_change_abs=abs(confidence_change),
        )


page_sequence = [BeforeQuestions, WikipediaDisplay, AfterQuestions, Results]
