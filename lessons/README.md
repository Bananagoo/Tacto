# Lessons

One YAML file per lesson. A lesson is data: a second lesson is a new file here, not new code, and changing wording never needs a code change.

At startup the server reads every `*.yaml` file in this directory (`server/tacto/lessons/loader.py`), validates it against the `Lesson` model (`server/tacto/lessons/models.py`) and stores it in the local database (`server/tacto/store/seed.py`). A file with a mistake stops the load with a message that names the file and the field.

`circuits-101.yaml` is the lesson for the demo. Its wording is a draft for the lesson author to edit.

## Shape of a file

```yaml
id: circuits-101            # unique across files
title: Circuits 101
language: en                # optional, defaults to en

concepts:                   # the learning graph: what this lesson teaches
  - id: closed_loop
    title: Closed loop
  - id: current
    title: Current
    requires: [closed_loop] # concepts that should come first

steps:                      # walked in order
  - id: series              # unique within the lesson
    teaches: [current]      # concept ids from the list above
    predict:                # optional
      say: "..."
      choices:              # two to four; shown on screen -> words that count when spoken
        both dimmer: [dimmer, darker]
        no change: [same, no change]
      answer: both dimmer   # one of the choices
      misconceptions:       # wrong choice -> what the tutor says about that idea, after the test
        no change: "..."
    build:
      say: "..."
      done_when: { topology: series, lit_bulbs: 2 }
    observe:
      say: "..."
    explain:
      say: "..."
    hints: ["...", "...", "..."]
```

A step always runs in the order predict → build → test → explain, whatever order the keys are written in. The learner predicts, makes the change on the mat, feels and sees the result (`observe`), and only then hears the explanation.

`done_when` lists conditions on the circuit on the mat; all of them must hold for the step to count as built.

| Key | Values |
|---|---|
| `status` | `empty`, `open`, `closed`, `short` |
| `bulbs` | number of bulbs on the mat |
| `lit_bulbs` | number of bulbs carrying current |
| `topology` | `none`, `single`, `series`, `parallel`, `mixed` |

An unknown key anywhere in the file is an error, so a typo cannot be silently ignored.

## Rules for the wording

The full rules are in `.claude/rules/lessons.md`. The ones the tests check on `circuits-101.yaml` (`server/tests/lessons/test_circuits_101_content.py`):

- Every line is spoken: one sentence, under 20 words, addressed to "you".
- No symbols or units that read badly aloud: no number with a unit, no `Ω`, `=` or `/`.
- A prediction has two to four choices and answers at least one wrong idea. A spoken keyword belongs to one choice only.
- Each step has a ladder of three hints: a smaller question, a pointer to where to look or touch, then a worked example on the learner's own circuit. No hint contains the answer.
- Vibration is current. The wheel is voltage. Never mix them.

## Things that bite

- Quote `"yes"` and `"no"` wherever they appear. YAML reads the bare words as true and false.
- Run `make check` after editing. It loads every file here and checks the rules above.
