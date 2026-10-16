# Manual POC Checklist (PRD Section 16)

Follow this checklist for testing the module with real external services (Google Meet + Fireflies.ai):

1. **Fireflies setup:**
   - Sign up at [Fireflies.ai](https://app.fireflies.ai).
   - Generate an API Key under Developer Settings.
   - Configure the Webhook URL in Fireflies Dashboard to:
     `<APP_BASE_URL>/api/v1/transcribe/webhooks/fireflies`
   - Copy the Webhook Secret.
   - Set in `transcribe/.env`:
     ```env
     FIREFLIES_API_KEY=<your_api_key>
     FIREFLIES_WEBHOOK_SECRET=<your_webhook_secret>
     ```

2. **Expose Local Server:**
   - Run server: `uvicorn app.main:app --port 8000`
   - Expose via ngrok: `ngrok http 8000`
   - Set `APP_BASE_URL` in `.env` to your public ngrok URL.

3. **Start Live Meeting:**
   - Start a Google Meet call with at least 3 participants.
   - Verbally announce recording consent: *"This meeting is being recorded and transcribed."*

4. **Dispatch Notetaker Bot:**
   - Make an API call to `POST /api/v1/transcribe/meetings`:
     ```json
     {
       "meeting_link": "<your_meet_link>",
       "project_id": "live_demo",
       "title": "Live Sprint Planning",
       "organizer_telegram_id": "<your_chat_id>",
       "consent_confirmed": true
     }
     ```
   - **Check:** Fireflies Notetaker bot requests to join -> Admit it.

5. **Spoken Commitment Scenarios:**
   - Speak clear task: *"I will finish the login page by Friday."*
   - Speak unassigned task: *"Someone should write the documentation report."*
   - Speak vague deadline: *"Anita, can you prepare the slides?" "Yes, sometime next week."*

6. **End Meeting & Verify Webhook:**
   - End the call.
   - Wait ~2 minutes for Fireflies to finish transcription.
   - Check server logs for `POST /api/v1/transcribe/webhooks/fireflies` -> status 200.

7. **Verify Telegram Notifications & Approvals:**
   - Check Telegram for summary message and task cards.
   - Unassigned task should send clarification: *"Who owns 'write documentation report'?"*
   - Tap **[Approve]** on a proposed task.
   - Verify task is handed off to task sink.
