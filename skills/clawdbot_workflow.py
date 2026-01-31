#!/usr/bin/env python3
"""
ClawdBot Workflow - Conversational Job Application System
==========================================================
Natural language interface for job queue management and applications.
"""
import os
import sys
import asyncio
import re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

from job_queue_manager import (
    JobQueueManager, 
    clawdbot_add_job, 
    clawdbot_get_queue, 
    clawdbot_get_stats,
    clawdbot_apply_next,
    clawdbot_apply_all
)


class ClawdBot:
    """ClawdBot conversational interface for job applications."""
    
    def __init__(self):
        self.manager = JobQueueManager()
        self.context = {
            'last_job': None,
            'last_action': None,
            'session_applied': 0
        }
    
    async def process_command(self, user_input: str) -> str:
        """Process natural language commands."""
        input_lower = user_input.lower().strip()
        
        # Queue status commands
        if any(kw in input_lower for kw in ['queue', 'jobs', 'list', 'show']):
            if 'stat' in input_lower:
                return clawdbot_get_stats()
            return clawdbot_get_queue()
        
        # Apply commands
        if 'apply' in input_lower:
            if 'all' in input_lower or 'queue' in input_lower:
                # Extract number if specified
                match = re.search(r'(\d+)', input_lower)
                max_apps = int(match.group(1)) if match else 5
                return await clawdbot_apply_all(max_apps)
            elif 'next' in input_lower or 'one' in input_lower:
                return await clawdbot_apply_next()
            else:
                # Check if specific job mentioned
                return await clawdbot_apply_next()
        
        # Add job commands
        if 'add' in input_lower or 'queue' in input_lower:
            # Try to extract URL from input
            url_match = re.search(r'https?://[^\s]+', user_input)
            if url_match:
                url = url_match.group(0)
                # Try to extract company and title
                return self._add_job_from_url(url)
        
        # Stats commands
        if 'stat' in input_lower or 'status' in input_lower:
            return clawdbot_get_stats()
        
        # Help
        if 'help' in input_lower:
            return self._get_help()
        
        # Default: show queue
        return f"I didn't understand that. Try:\n{self._get_help()}"
    
    def _add_job_from_url(self, url: str) -> str:
        """Add a job from URL, extracting info if possible."""
        # Extract company from URL
        company = "Unknown"
        title = "Job"
        
        if 'greenhouse' in url:
            match = re.search(r'for=(\w+)', url)
            if match:
                company = match.group(1).title()
            match = re.search(r'/jobs/(\d+)', url)
            if not match:
                match = re.search(r'token=(\d+)', url)
        elif 'lever' in url:
            match = re.search(r'lever\.co/([^/]+)', url)
            if match:
                company = match.group(1).replace('-', ' ').title()
        elif 'linkedin' in url:
            if 'vumedi' in url.lower():
                company = "VuMedi"
                title = "Brand Designer"
        
        return clawdbot_add_job(url, title, company)
    
    def _get_help(self) -> str:
        return """📚 ClawdBot Commands:
   • "show queue" - List jobs waiting to apply
   • "show stats" - Get queue statistics
   • "apply next" - Apply to the next job in queue
   • "apply all" or "apply 5" - Apply to multiple jobs
   • "add [URL]" - Add a job URL to the queue
   • "help" - Show this help"""


async def clawdbot_chat(message: str) -> str:
    """Main entry point for ClawdBot conversations."""
    bot = ClawdBot()
    return await bot.process_command(message)


async def main():
    """Interactive ClawdBot session."""
    print("=" * 60)
    print("🤖 ClawdBot - Job Application Assistant")
    print("=" * 60)
    print("Type 'help' for commands, 'quit' to exit.\n")
    
    bot = ClawdBot()
    
    # Show initial status
    print(clawdbot_get_stats())
    print()
    
    while True:
        try:
            user_input = input("You: ").strip()
            if not user_input:
                continue
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("👋 Goodbye!")
                break
            
            response = await bot.process_command(user_input)
            print(f"\n🤖 ClawdBot: {response}\n")
            
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")


# Quick test
if __name__ == "__main__":
    print("=" * 60)
    print("ClawdBot Workflow Test")
    print("=" * 60)
    
    async def test():
        bot = ClawdBot()
        
        # Test commands
        print("\n1. Show queue:")
        print(await bot.process_command("show queue"))
        
        print("\n2. Show stats:")
        print(await bot.process_command("show stats"))
        
        print("\n3. Add VuMedi job:")
        print(await bot.process_command("add https://www.linkedin.com/jobs/view/brand-designer-at-vumedi-4335836027/"))
        
        print("\n4. Apply to next job:")
        print(await bot.process_command("apply next"))
    
    asyncio.run(test())
