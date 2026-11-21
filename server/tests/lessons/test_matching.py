"""What the learner said or clicked becomes one of the prediction's choices, or nothing."""

from tacto.lessons.matching import match_choice

CHOICES = {
    "dimmer": ["dimmer", "darker", "less bright"],
    "same": ["same", "no change"],
    "brighter": ["brighter"],
}
YES_NO = {"yes": ["yes", "yeah", "pulse"], "no": ["no", "nothing", "nope"]}


def test_a_choice_name_matches_itself():
    assert match_choice("dimmer", CHOICES) == "dimmer"


def test_a_keyword_inside_a_sentence_matches():
    assert match_choice("I think it gets dimmer", CHOICES) == "dimmer"
    assert match_choice("it will be darker than before", CHOICES) == "dimmer"


def test_case_and_punctuation_are_ignored():
    assert match_choice("DIMMER!", CHOICES) == "dimmer"
    assert match_choice("  Brighter, I guess?  ", CHOICES) == "brighter"
    assert match_choice("the same.", CHOICES) == "same"


def test_a_keyword_can_be_a_phrase():
    assert match_choice("probably less bright", CHOICES) == "dimmer"
    assert match_choice("less, but bright", CHOICES) is None  # the words must be together


def test_a_keyword_must_be_a_whole_word():
    assert match_choice("I don't know", YES_NO) is None  # "know" contains "no"
    assert match_choice("eyes", YES_NO) is None  # "eyes" contains "yes"


def test_an_answer_matching_two_choices_is_not_an_answer():
    assert match_choice("dimmer or brighter", CHOICES) is None
    assert match_choice("yes, no, maybe", YES_NO) is None


def test_an_exact_choice_name_wins_over_keywords():
    # A button sends the choice name; it must win even though "no" is another choice's keyword.
    choices = {"no": ["nothing"], "same": ["no"]}

    assert match_choice("No.", choices) == "no"


def test_a_choice_name_with_several_words_matches_exactly():
    choices = {"the same": ["unchanged"], "goes out": ["dark"]}

    assert match_choice("The same!", choices) == "the same"


def test_an_apostrophe_does_not_split_a_word():
    # "don't" must not leave a stray "t" behind for a keyword to catch.
    assert match_choice("I don't think so", {"true": ["t"], "false": ["f"]}) is None


def test_text_matching_nothing_is_none():
    assert match_choice("purple", CHOICES) is None


def test_empty_text_is_none():
    assert match_choice("", CHOICES) is None
    assert match_choice("  ?! ", CHOICES) is None


def test_an_empty_keyword_never_matches():
    assert match_choice("anything at all", {"yes": ["", "?"], "no": ["nope"]}) is None
