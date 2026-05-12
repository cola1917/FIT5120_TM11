# Pair Programming Document

## What Is Pair Programming?

Pair programming is a collaborative software development practice where two team members work together on the same task. One person acts as the **Driver**, who writes the code, while the other acts as the **Navigator**, who reviews and guides the work. During a programming session, the roles may be swapped.

For this project, pair programming is used to improve code quality, share technical knowledge across the team, reduce misunderstandings, and make sure important features are reviewed while they are being developed.

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

Roles should rotate during longer sessions or across different tasks. A recommended rotation is every 30-45 minutes, or after completing a small feature step.

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

- Food scanning flow (frontend → backend → result display)
- Backend `/scan` endpoint and frontend API integration
- User profile creation and food preference storage
- Goal-based food recommendation logic
- Daily challenge API and mobile screen integration
- Meal Maker mini-game scoring and feedback
- Avatar EXP and level progression logic
- Food Quest Map feature integration
- Final feature testing and validation
- Onboarding flow optimisation
- README, testing reports, and project documentation

## 8.0 Actual Pair Programming Sessions

| Date | Driver | Navigator | Task | Description | Outcome |
|------|--------|-----------|------|-------------|---------|
| 16/03/26 | Henry | YiPing | Confirming the presentation style of the story | Once a child has chosen a storybook, how should it be presented—by turning the pages or by swiping? | Turning the pages helps prevent the child from seeing too much text at once and losing interest in reading. |
| 12/04/26 | ZiCheng | Henry | Recover the Outcome page in the story function | When integrating the front-end and back-end, I assumed this was part of the story, so I included it in the story’s page count. | The final adjustment is that “Outcome” now has its own page. |
| 21/04/26 | YiPing | Henry | Change the Avatar | Believing that the current Avatar is too ordinary to appeal to children, adjustments were made to the Avatar. | Make the avatar cuter and replace it. |
| 27/04/26 | Bohan | Henry | Change the food recommendation algorithm of the goal function | With the introduction of User Profiles, the food recommendation logic previously based on Goals should be revised. Recommendations should no longer be based solely on Goals, but should instead take into account both the child’s food preferences and their Goals. | Change the recommendation algorithm to better meet our requirements. |
| 28/04/26 | Zicheng | Henry | Change to food recommendation presentation styles in the goal function | If we simply recommend foods based solely on a child’s preferences, the risk is encouraging them to become fussy eaters. | Add a “Tiny Hero Challenge” to encourage children to try foods they don’t usually like. |
| 02/05/26 | Henry | YiPing | Improve Food Quest Map interaction flow | During testing, the original Food Quest Map flow contained too many steps and unclear instructions for children. The team reviewed how to simplify the interaction and improve readability. | Simplified the Food Quest Map interface and improved child-friendly guidance text. |
| 05/05/26 | YiPing | Henry | Debug API response handling between frontend and backend | During frontend and backend integration, inconsistent API responses caused some food recommendation pages to fail rendering correctly. | Standardised API response handling and improved error validation logic. |
| 08/05/26 | Bohan | Henry | Optimise Avatar EXP and level-up logic | The EXP progression and level-up calculations did not properly handle remaining EXP after levelling up. The team reviewed the logic and edge cases for Avatar progression. | Updated the EXP calculation logic and implemented EXP carry-over after level upgrades. |
| 10/05/26 | ZiCheng | Henry | Improve onboarding and profile setup experience | During user testing, some children experienced difficulty understanding the profile setup process and avatar selection flow. | Simplified onboarding instructions and improved avatar selection visuals. |
| 11/05/26 | Henry | Jiangtao | Final feature testing and validation | Before final submission, system-wide testing was conducted on story progression, game rewards, Avatar levels, and daily challenge features to identify integration and edge-case issues. | Multiple UI inconsistencies and functional bugs were resolved, improving overall feature stability and user experience. |
| 12/05/26 | Henry | Bohan | Review child-friendly wording and safety messages | The team reviewed whether system messages, food guidance, and Food Quest Map reminders were understandable and suitable for children aged 7–12. | Updated multiple UI texts and safety reminders using simpler and more child-friendly wording. |

## Evidence to Attach or Reference

When submitting pair programming evidence, the team can include:

- Git commit references or pull request links.
- Screenshots of the working feature.
- Testing notes or generated test reports.
- Meeting notes from the session.
- Before-and-after screenshots for UI changes.
- Short notes explaining role rotation and decisions made.

## Reflection

Pair programming supported this project by helping the team connect implementation decisions with the target users: children aged 7-12. Since NutriHeroes depends on both technical correctness and child-friendly interaction design, pairing helped catch problems earlier.

The practice is especially useful for features where multiple parts of the system interact, such as scanning food, receiving backend analysis, displaying health feedback, and recommending alternatives.
