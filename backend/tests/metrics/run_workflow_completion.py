"""
run_workflow_completion.py
──────────────────────────────
Paper, Table 2: "Workflow Completion Rate — Target >75% — Method: Analytics
tracking." This is a real-usage metric — it can only be computed from actual
people using the app end-to-end, not simulated. This script queries your
live database to compute it.

Definition used here:
  STARTED   = a Resume row exists (candidate completed Stage 1: Upload)
  COMPLETED = that resume has an InterviewSession with completed_at set,
              AND a FeedbackReport for that session,
              AND at least one TodoItem under that feedback report.
              (i.e. they made it through all 5 stages: Upload -> Role
              Selection -> Interview -> Feedback -> To-Do List)

Usage:
    cd backend
    python tests/metrics/run_workflow_completion.py

Before running this meaningfully, get a handful of real people (classmates,
friends) to actually use the app end to end — some who finish, some who
drop off partway is normal and expected, not a problem to hide.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from app import create_app
from app.extensions import db
from app.models.resume_model import Resume
from app.models.interview_session_model import InterviewSession
from app.models.feedback_model import FeedbackReport
from app.models.todo_model import TodoItem


def run():
    app = create_app()
    with app.app_context():
        total_started = db.session.query(Resume.id).distinct().count()

        completed_resume_ids = (
            db.session.query(Resume.id)
            .join(InterviewSession, InterviewSession.resume_id == Resume.id)
            .join(FeedbackReport, FeedbackReport.session_id == InterviewSession.id)
            .join(TodoItem, TodoItem.feedback_id == FeedbackReport.id)
            .filter(InterviewSession.completed_at.isnot(None))
            .distinct()
            .all()
        )
        total_completed = len(completed_resume_ids)

        print(f"Resumes uploaded (workflow started):   {total_started}")
        print(f"Resumes that reached the To-Do stage:  {total_completed}")

        if total_started == 0:
            print("\nNo resumes in the database yet — have some test users")
            print("actually use the app first, then re-run this script.")
            return

        rate = total_completed / total_started * 100
        print(f"\nWORKFLOW COMPLETION RATE: {round(rate, 1)}%   (paper target: >75%)")

        # Simple stage-by-stage breakdown, useful for explaining any drop-off
        sessions_started = db.session.query(InterviewSession.id).distinct().count()
        sessions_completed = (
            db.session.query(InterviewSession.id)
            .filter(InterviewSession.completed_at.isnot(None))
            .distinct()
            .count()
        )
        feedback_generated = db.session.query(FeedbackReport.id).distinct().count()

        print("\nFunnel breakdown:")
        print(f"  Resumes uploaded:              {total_started}")
        print(f"  Interview sessions started:    {sessions_started}")
        print(f"  Interview sessions completed:  {sessions_completed}")
        print(f"  Feedback reports generated:    {feedback_generated}")
        print(f"  Reached To-Do list:            {total_completed}")


if __name__ == "__main__":
    run()