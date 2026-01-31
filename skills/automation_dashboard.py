"""
AUTOMATION DASHBOARD - Operational Monitoring for ClawdBot
===========================================================

Provides:
- Real-time metrics display
- Cost tracking
- Success rate monitoring
- Application history
- CAPTCHA statistics
"""

import os
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List


class AutomationDashboard:
    """Central dashboard for ClawdBot automation monitoring."""
    
    def __init__(self, data_dir: str = None):
        if not data_dir:
            data_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
        
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
    
    def _load_json(self, filename: str) -> Dict:
        filepath = self.data_dir / filename
        if filepath.exists():
            with open(filepath, 'r') as f:
                return json.load(f)
        return {}
    
    def get_application_stats(self) -> Dict:
        """Get application submission statistics."""
        
        applied_file = self.data_dir / 'applied_jobs.csv'
        stats = {
            "total": 0,
            "today": 0,
            "this_week": 0,
            "this_month": 0,
            "by_platform": {},
            "by_status": {}
        }
        
        if not applied_file.exists():
            return stats
        
        today = datetime.now().date()
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)
        
        try:
            with open(applied_file, 'r') as f:
                lines = f.readlines()[1:]  # Skip header
                
                for line in lines:
                    parts = line.strip().split(',')
                    if len(parts) >= 4:
                        stats["total"] += 1
                        
                        # Parse date
                        try:
                            date_str = parts[0]
                            app_date = datetime.fromisoformat(date_str).date()
                            
                            if app_date == today:
                                stats["today"] += 1
                            if app_date >= week_ago:
                                stats["this_week"] += 1
                            if app_date >= month_ago:
                                stats["this_month"] += 1
                        except:
                            pass
                        
                        # Platform
                        if len(parts) > 4:
                            platform = parts[4] if len(parts) > 4 else "unknown"
                            stats["by_platform"][platform] = stats["by_platform"].get(platform, 0) + 1
        except:
            pass
        
        return stats
    
    def get_captcha_stats(self) -> Dict:
        """Get CAPTCHA resolution statistics."""
        
        captcha_metrics = self._load_json("captcha/captcha_metrics.json")
        
        if not captcha_metrics:
            return {
                "total": 0,
                "success_rate": 0,
                "total_cost": 0,
                "today_cost": 0,
                "by_tier": {}
            }
        
        today = datetime.now().strftime("%Y-%m-%d")
        today_stats = captcha_metrics.get("daily_stats", {}).get(today, {})
        
        total = captcha_metrics.get("total_challenges", 0)
        successes = (
            captcha_metrics.get("tier1_success", 0) +
            captcha_metrics.get("tier2_success", 0) +
            captcha_metrics.get("tier3_success", 0)
        )
        
        return {
            "total": total,
            "success_rate": (successes / total * 100) if total > 0 else 0,
            "total_cost": captcha_metrics.get("total_cost", 0),
            "today_cost": today_stats.get("cost", 0),
            "by_tier": {
                "auto": captcha_metrics.get("tier1_success", 0),
                "service": captcha_metrics.get("tier2_success", 0),
                "human": captcha_metrics.get("tier3_success", 0),
                "failed": captcha_metrics.get("failures", 0)
            },
            "by_type": captcha_metrics.get("by_type", {})
        }
    
    def get_document_stats(self) -> Dict:
        """Get document generation statistics."""
        
        feedback_data = self._load_json("generation_feedback.json")
        
        generations = feedback_data.get("generations", [])
        scores = feedback_data.get("feedback_scores", [])
        
        return {
            "total_generated": len(generations),
            "avg_score": sum(scores) / len(scores) if scores else 0,
            "successful_patterns": len(feedback_data.get("successful_patterns", [])),
            "failed_patterns": len(feedback_data.get("failed_patterns", []))
        }
    
    def get_cost_summary(self) -> Dict:
        """Get cost breakdown for the month."""
        
        captcha_stats = self.get_captcha_stats()
        
        # Estimate LLM costs (rough estimate based on generations)
        doc_stats = self.get_document_stats()
        llm_cost = doc_stats["total_generated"] * 0.01  # ~$0.01 per document
        
        return {
            "captcha_cost": captcha_stats["total_cost"],
            "llm_cost_estimate": llm_cost,
            "total_estimate": captcha_stats["total_cost"] + llm_cost,
            "daily_budget_used": captcha_stats["today_cost"]
        }
    
    def render_dashboard(self) -> str:
        """Render the full dashboard as text."""
        
        app_stats = self.get_application_stats()
        captcha_stats = self.get_captcha_stats()
        doc_stats = self.get_document_stats()
        cost_stats = self.get_cost_summary()
        
        dashboard = f"""
╔══════════════════════════════════════════════════════════════════╗
║                    CLAWDBOT AUTOMATION DASHBOARD                  ║
║                    {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}                         ║
╠══════════════════════════════════════════════════════════════════╣
║                       📊 APPLICATION STATS                        ║
╠══════════════════════════════════════════════════════════════════╣
║  Total Applications:     {app_stats['total']:>6}                                  ║
║  Today:                  {app_stats['today']:>6}                                  ║
║  This Week:              {app_stats['this_week']:>6}                                  ║
║  This Month:             {app_stats['this_month']:>6}                                  ║
╠══════════════════════════════════════════════════════════════════╣
║                       🔐 CAPTCHA STATS                            ║
╠══════════════════════════════════════════════════════════════════╣
║  Total Challenges:       {captcha_stats['total']:>6}                                  ║
║  Success Rate:           {captcha_stats['success_rate']:>5.1f}%                                 ║
║  ├─ Auto (Tier 1):       {captcha_stats['by_tier'].get('auto', 0):>6}                                  ║
║  ├─ Service (Tier 2):    {captcha_stats['by_tier'].get('service', 0):>6}                                  ║
║  ├─ Human (Tier 3):      {captcha_stats['by_tier'].get('human', 0):>6}                                  ║
║  └─ Failed:              {captcha_stats['by_tier'].get('failed', 0):>6}                                  ║
╠══════════════════════════════════════════════════════════════════╣
║                       📄 DOCUMENT GENERATION                      ║
╠══════════════════════════════════════════════════════════════════╣
║  Total Generated:        {doc_stats['total_generated']:>6}                                  ║
║  Avg Quality Score:      {doc_stats['avg_score']:>5.1f}/10                                ║
║  Successful Patterns:    {doc_stats['successful_patterns']:>6}                                  ║
╠══════════════════════════════════════════════════════════════════╣
║                       💰 COST SUMMARY                             ║
╠══════════════════════════════════════════════════════════════════╣
║  CAPTCHA Services:       ${cost_stats['captcha_cost']:>6.2f}                                ║
║  LLM (estimate):         ${cost_stats['llm_cost_estimate']:>6.2f}                                ║
║  ───────────────────────────────                                  ║
║  Total This Month:       ${cost_stats['total_estimate']:>6.2f}                                ║
║  Today's Spend:          ${cost_stats['daily_budget_used']:>6.2f}                                ║
╚══════════════════════════════════════════════════════════════════╝
"""
        return dashboard
    
    def render_compact(self) -> str:
        """Render compact dashboard for Slack."""
        
        app_stats = self.get_application_stats()
        captcha_stats = self.get_captcha_stats()
        cost_stats = self.get_cost_summary()
        
        return f"""*ClawdBot Status*
📊 Applications: {app_stats['today']} today / {app_stats['this_week']} this week
🔐 CAPTCHA: {captcha_stats['success_rate']:.0f}% success rate
💰 Cost: ${cost_stats['total_estimate']:.2f} this month"""
    
    def get_recommendations(self) -> List[str]:
        """Get operational recommendations based on current stats."""
        
        recs = []
        
        captcha_stats = self.get_captcha_stats()
        cost_stats = self.get_cost_summary()
        app_stats = self.get_application_stats()
        
        # Low success rate
        if captcha_stats['success_rate'] < 70 and captcha_stats['total'] > 10:
            recs.append("⚠️ CAPTCHA success rate below 70%. Consider upgrading service tier.")
        
        # High human intervention
        human_rate = captcha_stats['by_tier'].get('human', 0) / max(captcha_stats['total'], 1)
        if human_rate > 0.5:
            recs.append("💡 High human intervention rate. Enable 2Captcha for automation.")
        
        # Budget concerns
        if cost_stats['daily_budget_used'] > 0.8:
            recs.append("💰 Approaching daily budget limit. Consider increasing or pacing submissions.")
        
        # Low volume
        if app_stats['this_week'] < 5:
            recs.append("📈 Low application volume. Consider expanding job search criteria.")
        
        # High volume risk
        if app_stats['today'] > 20:
            recs.append("⚠️ High daily volume may trigger rate limits. Consider pacing.")
        
        return recs if recs else ["✅ All systems operating normally"]


def show_dashboard():
    """Display the dashboard."""
    dashboard = AutomationDashboard()
    print(dashboard.render_dashboard())
    
    recs = dashboard.get_recommendations()
    if recs:
        print("\n📋 RECOMMENDATIONS:")
        for rec in recs:
            print(f"   {rec}")


def get_slack_status() -> str:
    """Get compact status for Slack."""
    dashboard = AutomationDashboard()
    return dashboard.render_compact()


if __name__ == "__main__":
    show_dashboard()
