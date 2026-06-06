# Session note: latest-message priority during memory/profile/self-description cleanup

## Trigger

Use this note when a session involves memory, user profile, self-description, identity files, or a compacted conversation summary.

## Lesson

A compacted context summary and prior tool state can make the assistant continue a previous task instead of answering the user's latest request. This is especially harmful when the user asks to analyze and organize memory/profile/self-description files: the correct action is not to finish the prior rule rewrite, but to execute the requested cleanup class directly.

## Correct workflow

1. Treat the latest user message as the active task.
2. If the user asks to analyze and organize memory/profile/self-description, run the cleanup workflow immediately:
   - locate governing files;
   - archive originals;
   - analyze stale, duplicate, conflicting, or transient content;
   - rewrite current-effective versions;
   - verify core terms exist and stale conflict signals are absent;
   - report concisely.
3. If the user sends a bare “？” or “什么意思” after a report, first assume the prior answer missed the requested task or lacked evidence.
4. Correct course by doing the task; do not defend the prior response.

## Pitfall to avoid

Do not let a previous task’s todos, summaries, or half-finished edits override the current user instruction. A final report about the wrong task is still a failure even if the edits were valid.
