---
name: incident-command-mindset
kind: brain
description: Use when an agent must run or support a coordinated response: leading a security incident, organizing a multi-person outage response, structuring war-room communication, or deciding who does what when everything is on fire. Provides incident command reasoning: one commander with clear authority, limited span of control, objectives before actions, rhythmic communication, and documentation as you go. Load this brain when the response involves more than one person and chaos is the default outcome.
version: 1.0.0
provides:
  - Single-commander authority structure
  - Span-of-control management
  - Objectives-before-actions planning
  - Rhythmic communication cadence
  - Live documentation discipline
  - Role clarity under pressure
used_by: []
---

Incidents fail more often from chaos than from technical difficulty. Five smart people all "helping" without coordination will trip over each other, duplicate work, miss the critical task, and lose the timeline. Incident command is the antidote: a simple structure borrowed from emergency services where one person commands, everyone has a role, objectives come before actions, and communication runs on a rhythm. It matters because the first hour of an incident sets its trajectory, and an hour of coordinated response beats a day of brilliant individuals working at cross purposes.

## Core mental models

**One commander, clear authority.** Exactly one person owns the incident: they set objectives, approve major actions, and resolve conflicts. Not a committee, not "whoever is senior," one named human. Everyone else advises and executes. This feels hierarchical and it is, because incidents need decisions faster than consensus allows. The commander does not do the technical work; they run the response.

**Span of control: nobody manages more than seven.** If one person is directly coordinating more than about five to seven people or workstreams, coordination collapses. Split into roles: operations (doing the technical work), communications (talking to stakeholders), scribe (writing everything down), and subject experts as needed. Small teams can double up roles, but the roles must exist and be named.

**Objectives before actions.** Before anyone touches a keyboard, the commander states the current objectives in priority order: "1. Stop the bleeding (contain). 2. Understand scope. 3. Preserve evidence." Every proposed action is then judged against the objectives. This stops the classic failure where someone starts rebuilding servers (recovery) while the attacker is still inside (containment not done). Sequence matters more than speed.

**Communicate on a rhythm.** Chaos loves silence. Set a battle rhythm: status updates every 15 or 30 minutes, same format each time (what we know, what we are doing, what we need). The commander runs it, the scribe records it. Stakeholders get updates on a slower rhythm so they stop interrupting the workers. Rhythm turns panic into process.

## Operating checklist

1. Declare the incident and name the commander. Say it out loud: "I am incident commander."
2. Assign the core roles: operations lead, communications, scribe. Double up only if the team is tiny.
3. State the objectives in priority order. Write them where everyone can see.
4. Establish the rhythm: tactical updates every 15-30 minutes, stakeholder updates hourly.
5. Start the timeline immediately: every action and observation logged with a timestamp.
6. Scope before you fix: understand what is affected before you start changing things.
7. Approve major actions through the commander: isolations, shutdowns, notifications, wipes.
8. Keep one shared picture: a single channel or doc that is the source of truth. Kill side channels.
9. Rotate people before they break: incidents are marathons that feel like sprints. Plan relief.
10. Stand down formally: declare the incident over, schedule the postmortem, thank the team.

## Heuristics

- If two people think they are in charge, nobody is. Name the commander in the first five minutes.
- The scribe is not optional. The timeline is the postmortem, the evidence, and the legal record.
- No action without an objective it serves. "Doing something" is not a strategy.
- Update stakeholders before they ask. Silence breeds escalations that steal your workers.
- Contain first, understand second, recover third, lessons last. The order is the discipline.
- If the war room has twenty people talking, split it: workers in one channel, observers in another.
- Tired responders make bad calls. A rested second shift beats a heroic first shift.
- Declare "incident over" explicitly. Otherwise it fades without learning.

## Anti-patterns

- **Committee command.** Decisions by consensus during a breach. Slow, and nobody owns the outcome.
- **Fixing before scoping.** Rebuilding systems while the attacker still has access. You will rebuild twice.
- **No scribe.** The timeline reconstructed from memory a week later, which is to say, fiction.
- **Side channels.** Decisions made in DMs that the commander never hears about. The shared picture shatters.
- **Hero shifts.** The same three people for 18 hours straight, making the worst decisions at hour 16.

## Worked example

A ransomware alert fires at 02:00. The on-call engineer declares the incident and names herself commander (one commander, minute five). Roles: a second engineer takes operations, a third takes scribe, stakeholder comms goes to the manager on a 60-minute rhythm. Objectives posted: 1. Contain spread. 2. Determine scope and patient zero. 3. Preserve evidence. Tactical rhythm: every 20 minutes. Operations isolates hosts per the commander's approval, never freelancing. The scribe's timeline captures every isolation time, which later becomes the evidence chain. At 03:00 the manager tells executives "contained, assessing scope, next update 04:00," and the execs stop calling the engineers. At 06:00 a rested second shift takes over with the full timeline. Containment holds, scope is known, evidence is intact, and nobody burned out. The response worked because the structure worked, not because anyone was heroic.
