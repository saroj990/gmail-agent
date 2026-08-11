# Testing Strategy

Test each layer independently.

## Gmail

```text
Can authenticate?
Can list messages?
Can read message?
```

## Parser

```text
Can parse plain text?
Can parse HTML?
Can parse multipart?
```

## Classifier

```text
Does valid email return valid JSON?
Does invalid model output get rejected?
```

## Agent

```text
IMPORTANT → no modification
TO_PROCESS → correct action
UNKNOWN → no action
```

## Gmail Actions

Test against one test email before batch processing.
