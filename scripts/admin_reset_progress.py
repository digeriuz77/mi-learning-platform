#!/usr/bin/env python3
"""
Admin User Progress Management Script

Provides admin functionality to reset user progress in the database.
Uses Supabase service role key for admin access.

Usage:
    python scripts/admin_reset_progress.py                    # Interactive menu
    python scripts/admin_reset_progress.py --list-users      # List all users
    python scripts/admin_reset_progress.py --reset-user USER_ID  # Reset specific user
    python scripts/admin_reset_progress.py --reset-all       # Reset ALL users
"""

import json
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client
import getpass

# Load environment variables
load_dotenv()


def get_supabase_admin():
    """Create admin Supabase client using service role key."""
    supabase_url = os.getenv("SUPABASE_URL")
    service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

    if not supabase_url or not service_role_key:
        print("Error: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in .env")
        sys.exit(1)

    return create_client(supabase_url, service_role_key)


def list_users(supabase, limit=100):
    """List all users with their progress stats."""
    print("\n" + "=" * 70)
    print("USER LIST")
    print("=" * 70)

    try:
        response = supabase.table("user_profiles").select("*").execute()
        users = response.data

        if not users:
            print("No users found.")
            return

        print(f"\nTotal users: {len(users)}\n")
        print(f"{'Email/ID':<40} {'Points':<10} {'Level':<8} {'Modules':<10}")
        print("-" * 70)

        for user in users:
            display_name = user.get("display_name", "N/A") or "N/A"
            user_id = user.get("user_id", "")[:8]
            points = user.get("total_points", 0)
            level = user.get("level", 1)
            modules = user.get("modules_completed", 0)
            print(f"{display_name:<40} {points:<10} {level:<8} {modules:<10}")

    except Exception as e:
        print(f"Error listing users: {e}")


def reset_user_progress(supabase, user_id, force=False):
    """Reset progress for a specific user."""
    print(f"\nResetting progress for user: {user_id}")

    # Confirm action
    if not force:
        confirm = input("Are you sure? Type 'yes' to confirm: ")
        if confirm.lower() != "yes":
            print("Cancelled.")
            return
    else:
        print("  (--yes flag provided, skipping confirmation)")

    try:
        # 1. Delete user's progress records
        progress_response = supabase.table("user_progress").delete().eq("user_id", user_id).execute()
        print(f"  - Deleted user_progress records")

        # 2. Delete user's dialogue attempts
        attempts_response = supabase.table("dialogue_attempts").delete().eq("user_id", user_id).execute()
        print(f"  - Deleted dialogue_attempts records")

        # 3. Reset user's profile stats
        profile_response = (
            supabase.table("user_profiles")
            .update(
                {
                    "total_points": 0,
                    "level": 1,
                    "modules_completed": 0,
                    "change_talk_evoked": 0,
                    "reflections_offered": 0,
                    "technique_mastery": {},
                    "updated_at": "now()",
                }
            )
            .eq("user_id", user_id)
            .execute()
        )
        print(f"  - Reset user_profiles stats")

        print("\n[SUCCESS] User progress reset successfully!")

    except Exception as e:
        print(f"\n[ERROR] Failed to reset user progress: {e}")


def reset_all_progress(supabase, force=False):
    """Reset progress for ALL users."""
    print("\n" + "=" * 70)
    print("WARNING: This will reset progress for ALL users!")
    print("=" * 70)

    # Double confirmation
    if not force:
        confirm1 = input("Type 'reset all' to confirm: ")
        if confirm1.lower() != "reset all":
            print("Cancelled.")
            return

        confirm2 = input("Are you ABSOLUTELY sure? Type 'yes I understand': ")
        if confirm2.lower() != "yes i understand":
            print("Cancelled.")
            return
    else:
        print("  (--yes flag provided, skipping confirmation)")

    try:
        # 1. Get all user IDs
        users_response = supabase.table("user_profiles").select("user_id").execute()
        users = users_response.data

        if not users:
            print("No users to reset.")
            return

        user_ids = [u["user_id"] for u in users]
        print(f"\nFound {len(user_ids)} users to reset...")

        # 2. Delete all progress records
        if user_ids:
            progress_response = supabase.table("user_progress").delete().in_("user_id", user_ids).execute()
            print(f"  - Deleted user_progress records")

            attempts_response = supabase.table("dialogue_attempts").delete().in_("user_id", user_ids).execute()
            print(f"  - Deleted dialogue_attempts records")

        # 3. Reset all profiles
        profiles_response = (
            supabase.table("user_profiles")
            .update(
                {
                    "total_points": 0,
                    "level": 1,
                    "modules_completed": 0,
                    "change_talk_evoked": 0,
                    "reflections_offered": 0,
                    "technique_mastery": {},
                    "updated_at": "now()",
                }
            )
            .execute()
        )

        print(f"  - Reset {len(profiles_response.data)} user_profiles")

        print(f"\n[SUCCESS] Reset progress for {len(user_ids)} users!")

    except Exception as e:
        print(f"\n[ERROR] Failed to reset all progress: {e}")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Admin user progress management")
    parser.add_argument("--list-users", action="store_true", help="List all users")
    parser.add_argument("--reset-user", metavar="USER_ID", help="Reset progress for specific user")
    parser.add_argument("--reset-all", action="store_true", help="Reset progress for ALL users")
    parser.add_argument("--yes", "-y", action="store_true", help="Skip confirmation prompts")

    args = parser.parse_args()

    supabase = get_supabase_admin()

    if args.list_users:
        list_users(supabase)
    elif args.reset_user:
        reset_user_progress(supabase, args.reset_user, force=args.yes)
    elif args.reset_all:
        reset_all_progress(supabase, force=args.yes)
    else:
        # Interactive mode
        print("\n" + "=" * 50)
        print("Admin User Progress Management")
        print("=" * 50)
        print("1. List all users")
        print("2. Reset specific user progress")
        print("3. Reset ALL users progress")
        print("4. Exit")

        choice = input("\nSelect option (1-4): ")

        if choice == "1":
            list_users(supabase)
        elif choice == "2":
            user_id = input("Enter user_id to reset: ").strip()
            if user_id:
                reset_user_progress(supabase, user_id)
            else:
                print("No user ID provided.")
        elif choice == "3":
            reset_all_progress(supabase, force=False)
        else:
            print("Exiting.")


if __name__ == "__main__":
    main()
