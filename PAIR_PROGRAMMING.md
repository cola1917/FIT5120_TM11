# Pair Programming Document

## What Is Pair Programming?

Pair programming is a collaborative software development practice where two team members work together on the same task. One person acts as the **Driver**, who writes the code, while the other acts as the **Navigator**, who reviews the approach, checks logic, suggests improvements, and thinks ahead about edge cases. The two roles should rotate regularly so both team members contribute to implementation and review.

For this project, pair programming is used to improve code quality, share technical knowledge across the team, reduce misunderstandings, and make sure important features are reviewed while they are being built.

## Project Context

NutriHeroes is a mobile nutrition application for children aged 7-12. The project includes:

- An Expo React Native mobile application
- A FastAPI backend service
- Food image scanning and nutrition analysis
- Personalised food recommendations
- User profile and food preference management
- Daily healthy challenges
- Educational stories and mini-games

Because the system includes both frontend and backend work, pair programming helps the team align user experience, API contracts, data flow, and testing expectations.

## Pair Programming Goals

- Build shared understanding of important features.
- Detect bugs and usability issues earlier.
- Keep frontend and backend implementation aligned.
- Improve consistency in code style and naming.
- Help team members learn from each other.
- Produce clearer documentation and testing notes.

## Roles

### Driver

The Driver is responsible for:

- Writing code or documentation during the session.
- Following the agreed implementation plan.
- Explaining what is being changed while working.
- Running relevant checks or tests when needed.

### Navigator

The Navigator is responsible for:

- Reviewing the code or documentation as it is created.
- Checking whether the solution matches the feature requirement.
- Thinking about edge cases, errors, and user experience.
- Suggesting improvements before the work is finalised.

### Role Rotation

Roles should rotate during longer sessions or across different tasks. A recommended rotation is every 30-45 minutes, or after completing a small feature step such as UI layout, API integration, validation, or testing.

## Pair Programming Workflow

1. Define the task clearly.
2. Agree on the expected outcome before coding.
3. Choose Driver and Navigator roles.
4. Review the related files, APIs, or user flow.
5. Implement the change together.
6. Test or manually verify the result.
7. Record the session summary and any follow-up tasks.

## Communication Rules

- Discuss the approach before making major changes.
- Explain decisions in simple and specific terms.
- Ask questions when the purpose of a file or feature is unclear.
- Keep feedback focused on the code, not the person.
- Record unresolved issues instead of leaving them implicit.
- Rotate roles so each person has a chance to drive and review.

## Areas Suitable for Pair Programming

The following parts of NutriHeroes are especially suitable for pair programming:

- Food scanning flow from camera capture to analysis result.
- Backend `/scan` endpoint and frontend API integration.
- User profile creation and food preference storage.
- Goal-based food recommendation logic.
- Daily challenge API and mobile screen integration.
- Meal Maker mini-game scoring and feedback.
- README, testing reports, and project documentation.

## 8.0 Actual Pair Programming Sessions

| Date | Driver | Navigator | Task | Description | Outcome |
|------|--------|-----------|------|-------------|---------|
| 16/03/26 | Henry | YiPing | Confirming the presentation style of the story | Once a child has chosen a storybook, how should it be presented by turning the pages or by swiping? | Turning the pages helps prevent the child from seeing too much text at once and losing interest in reading. |
| 12/04/26 | ZiCheng | Henry | Recover the Outcome page in the story function | When integrating the frontend and backend, I assumed this was part of the story, so I included it in the story's page count. | The final adjustment is that "Outcome" now has its own page. |
| 21/04/26 | YiPing | Henry | Change the Avatar | Believing that the current Avatar is too ordinary to appeal to children, adjustments were made to the Avatar. | Make the avatar cuter and replace it. |
| 27/04/26 | Bohan | Henry | Change the food recommendation algorithm of the  goal function | With the introduction of User Profiles, the food recommendation logic previously based on Goals should be revised. Recommendations should no longer be based solely on Goals, but should instead take into account both the child's food preferences and their Goals. | Change the recommendation algorithm to better meet our requirements. |
| 28/04/26 | Zicheng | Henry | Change to food recommendation presentation styles in the goal function | If we simply recommend foods based solely on a child's preferences, the risk is encouraging them to become fussy eaters. | Add a "Tiny Hero Challenge" to encourage children to try foods they do not usually like. |

## Evidence to Attach or Reference

When submitting pair programming evidence, the team can include:

- Git commit references or pull request links.
- Screenshots of the working feature.
- Testing notes or generated test reports.
- Meeting notes from the session.
- Before-and-after screenshots for UI changes.
- Short notes explaining role rotation and decisions made.

## Reflection

Pair programming supported this project by helping the team connect implementation decisions with the target users: children aged 7-12. Since NutriHeroes depends on both technical correctness and child-friendly communication, having one person implement while another reviews the flow helped identify issues in wording, navigation, error handling, and feature consistency earlier than working alone.

The practice is especially useful for features where multiple parts of the system interact, such as scanning food, receiving backend analysis, displaying health feedback, and recommending alternatives. Future sessions should continue to record roles, decisions, and follow-up tasks so the team has clear evidence of collaboration and shared ownership.
