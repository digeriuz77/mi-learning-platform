"""
Report Export API Routes - PDF and styled HTML export for analysis reports

Provides endpoints to export conversation analysis reports in various formats.
Uses client-side PDF generation via styled HTML for maximum compatibility.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

from app.core.auth import get_current_user, AuthContext
from app.models.chat import ConversationAnalysis

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/export", tags=["Export"])


class ExportRequest(BaseModel):
    """Request to export an analysis report"""

    analysis: Dict[str, Any]
    format: str = "html"  # html, json
    title: Optional[str] = "MI Practice Analysis Report"


def _generate_html_report(
    analysis: Dict[str, Any],
    title: str = "MI Practice Analysis Report",
    generated_at: Optional[str] = None,
) -> str:
    """Generate a styled HTML report from analysis data."""

    if not generated_at:
        generated_at = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    # Extract analysis data
    overall_score = analysis.get("overall_score", 0)
    foundational = analysis.get("foundational_trust_safety", 0)
    empathy = analysis.get("empathic_partnership_autonomy", 0)
    empowerment = analysis.get("empowerment_clarity", 0)
    mi_spirit = analysis.get("mi_spirit_score", 0)

    mi_spirit_components = {
        "Partnership": analysis.get("partnership_demonstrated", False),
        "Acceptance": analysis.get("acceptance_demonstrated", False),
        "Compassion": analysis.get("compassion_demonstrated", False),
        "Evocation": analysis.get("evocation_democation_demonstrated", False),
    }

    techniques_count = analysis.get("techniques_count", {})
    strengths = analysis.get("strengths", [])
    areas_for_improvement = analysis.get("areas_for_improvement", [])
    transcript_summary = analysis.get("transcript_summary", "")
    summary = analysis.get("summary", "")
    suggestions = analysis.get("suggestions_for_next_time", [])
    client_movement = analysis.get("client_movement", "stable")
    change_talk = analysis.get("change_talk_evoked", False)

    # Calculate color based on score
    def score_color(score):
        if score >= 4:
            return "#27ae60"  # Green
        elif score >= 3:
            return "#f39c12"  # Orange
        else:
            return "#e74c3c"  # Red

    # Build techniques list
    techniques_html = ""
    if techniques_count:
        for tech, count in techniques_count.items():
            if count > 0:
                tech_name = tech.replace("_", " ").title()
                techniques_html += f'<div class="technique-item"><span class="technique-name">{tech_name}:</span> <span class="technique-count">{count}</span></div>'

    # Build strengths list
    strengths_html = ""
    if strengths:
        for strength in strengths:
            strengths_html += f'<li class="strength-item">{strength}</li>'

    # Build areas for improvement list
    improvements_html = ""
    if areas_for_improvement:
        for area in areas_for_improvement:
            improvements_html += f'<li class="improvement-item">{area}</li>'

    # Build suggestions list
    suggestions_html = ""
    if suggestions:
        for suggestion in suggestions:
            suggestions_html += f'<li class="suggestion-item">{suggestion}</li>'

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        @media print {{
            body {{ print-color-adjust: exact; -webkit-print-color-adjust: exact; }}
        }}
        
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            background: #f5f5f5;
            padding: 20px;
        }}
        
        .container {{
            max-width: 800px;
            margin: 0 auto;
            background: white;
            padding: 40px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        
        .header {{
            text-align: center;
            border-bottom: 3px solid #3498db;
            padding-bottom: 20px;
            margin-bottom: 30px;
        }}
        
        .header h1 {{
            color: #2c3e50;
            font-size: 28px;
            margin-bottom: 10px;
        }}
        
        .header .subtitle {{
            color: #7f8c8d;
            font-size: 14px;
        }}
        
        .score-overview {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
            gap: 15px;
            margin-bottom: 30px;
        }}
        
        .score-card {{
            background: #f8f9fa;
            padding: 15px;
            border-radius: 8px;
            text-align: center;
            border-left: 4px solid #3498db;
        }}
        
        .score-card.highlight {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border-left: none;
        }}
        
        .score-value {{
            font-size: 32px;
            font-weight: bold;
            margin-bottom: 5px;
        }}
        
        .score-label {{
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        
        .section {{
            margin-bottom: 25px;
        }}
        
        .section h2 {{
            color: #2c3e50;
            font-size: 20px;
            margin-bottom: 15px;
            padding-bottom: 8px;
            border-bottom: 2px solid #ecf0f1;
        }}
        
        .section h3 {{
            color: #34495e;
            font-size: 16px;
            margin-bottom: 10px;
        }}
        
        .summary-box {{
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            border-left: 4px solid #3498db;
            margin-bottom: 15px;
        }}
        
        .transcript-summary {{
            background: #e8f4fd;
            padding: 20px;
            border-radius: 8px;
            border-left: 4px solid #3498db;
            margin-bottom: 20px;
        }}
        
        .mi-spirit-grid {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 10px;
            margin-top: 10px;
        }}
        
        .mi-spirit-item {{
            display: flex;
            align-items: center;
            padding: 10px;
            background: #f8f9fa;
            border-radius: 6px;
        }}
        
        .mi-spirit-item.present {{
            background: #d4edda;
            border-left: 3px solid #28a745;
        }}
        
        .mi-spirit-item.absent {{
            background: #f8d7da;
            border-left: 3px solid #dc3545;
        }}
        
        .status-icon {{
            margin-right: 10px;
            font-size: 18px;
        }}
        
        .techniques-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 10px;
            margin-top: 10px;
        }}
        
        .technique-item {{
            display: flex;
            justify-content: space-between;
            padding: 8px 12px;
            background: #f8f9fa;
            border-radius: 6px;
        }}
        
        .technique-count {{
            font-weight: bold;
            color: #3498db;
        }}
        
        .list-section {{
            background: #f8f9fa;
            padding: 15px;
            border-radius: 8px;
            margin-top: 10px;
        }}
        
        .list-section ul {{
            list-style: none;
            padding: 0;
        }}
        
        .list-section li {{
            padding: 8px 0;
            padding-left: 25px;
            position: relative;
        }}
        
        .list-section li:before {{
            content: "";
            position: absolute;
            left: 0;
            top: 14px;
            width: 8px;
            height: 8px;
            border-radius: 50%;
        }}
        
        .strength-item:before {{
            background: #27ae60;
        }}
        
        .improvement-item:before {{
            background: #e74c3c;
        }}
        
        .suggestion-item:before {{
            background: #3498db;
        }}
        
        .client-movement {{
            display: inline-block;
            padding: 8px 16px;
            border-radius: 20px;
            font-weight: bold;
            text-transform: uppercase;
            font-size: 12px;
        }}
        
        .movement-toward {{
            background: #d4edda;
            color: #155724;
        }}
        
        .movement-away {{
            background: #f8d7da;
            color: #721c24;
        }}
        
        .movement-stable {{
            background: #fff3cd;
            color: #856404;
        }}
        
        .footer {{
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #ecf0f1;
            text-align: center;
            color: #7f8c8d;
            font-size: 12px;
        }}
        
        .print-button {{
            display: inline-block;
            margin: 20px 0;
            padding: 12px 24px;
            background: #3498db;
            color: white;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-size: 14px;
            text-decoration: none;
        }}
        
        .print-button:hover {{
            background: #2980b9;
        }}
        
        @media print {{
            body {{
                background: white;
                padding: 0;
            }}
            .container {{
                box-shadow: none;
                max-width: 100%;
            }}
            .no-print {{
                display: none;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{title}</h1>
            <p class="subtitle">Generated: {generated_at}</p>
        </div>
        
        <div class="no-print" style="text-align: center;">
            <button class="print-button" onclick="window.print()">Print / Save as PDF</button>
        </div>
        
        <div class="score-overview">
            <div class="score-card highlight">
                <div class="score-value">{overall_score:.1f}</div>
                <div class="score-label">Overall Score</div>
            </div>
            <div class="score-card">
                <div class="score-value" style="color: {score_color(foundational)}">{foundational:.1f}</div>
                <div class="score-label">Trust & Safety</div>
            </div>
            <div class="score-card">
                <div class="score-value" style="color: {score_color(empathy)}">{empathy:.1f}</div>
                <div class="score-label">Empathy & Partnership</div>
            </div>
            <div class="score-card">
                <div class="score-value" style="color: {score_color(empowerment)}">{empowerment:.1f}</div>
                <div class="score-label">Empowerment & Clarity</div>
            </div>
            <div class="score-card">
                <div class="score-value" style="color: {score_color(mi_spirit)}">{mi_spirit:.1f}</div>
                <div class="score-label">MI Spirit</div>
            </div>
        </div>
        
        <div class="section">
            <h2>Conversation Summary</h2>
            <div class="transcript-summary">
                <p>{transcript_summary or "No transcript summary available."}</p>
            </div>
        </div>
        
        <div class="section">
            <h2>Performance Summary</h2>
            <div class="summary-box">
                <p>{summary or "No summary available."}</p>
            </div>
        </div>
        
        <div class="section">
            <h2>MI Spirit Assessment</h2>
            <div class="mi-spirit-grid">
                <div class="mi-spirit-item {"present" if mi_spirit_components["Partnership"] else "absent"}">
                    <span class="status-icon">{"&#10004;" if mi_spirit_components["Partnership"] else "&#10008;"}</span>
                    <span>Partnership</span>
                </div>
                <div class="mi-spirit-item {"present" if mi_spirit_components["Acceptance"] else "absent"}">
                    <span class="status-icon">{"&#10004;" if mi_spirit_components["Acceptance"] else "&#10008;"}</span>
                    <span>Acceptance</span>
                </div>
                <div class="mi-spirit-item {"present" if mi_spirit_components["Compassion"] else "absent"}">
                    <span class="status-icon">{"&#10004;" if mi_spirit_components["Compassion"] else "&#10008;"}</span>
                    <span>Compassion</span>
                </div>
                <div class="mi-spirit-item {"present" if mi_spirit_components["Evocation"] else "absent"}">
                    <span class="status-icon">{"&#10004;" if mi_spirit_components["Evocation"] else "&#10008;"}</span>
                    <span>Evocation</span>
                </div>
            </div>
        </div>
        
        <div class="section">
            <h2>Techniques Used</h2>
            <div class="techniques-grid">
                {techniques_html or "<p>No techniques identified.</p>"}
            </div>
        </div>
        
        <div class="section">
            <h2>Client Movement</h2>
            <span class="client-movement movement-{client_movement}">
                {client_movement.replace("_", " ").title()}
            </span>
            {'<p style="margin-top: 10px; color: #27ae60;">&#10004; Change talk was evoked</p>' if change_talk else ""}
        </div>
        
        <div class="section">
            <h2>Strengths</h2>
            <div class="list-section">
                <ul>
                    {strengths_html or "<li>No specific strengths identified.</li>"}
                </ul>
            </div>
        </div>
        
        <div class="section">
            <h2>Areas for Improvement</h2>
            <div class="list-section">
                <ul>
                    {improvements_html or "<li>No specific areas for improvement identified.</li>"}
                </ul>
            </div>
        </div>
        
        <div class="section">
            <h2>Suggestions for Next Time</h2>
            <div class="list-section">
                <ul>
                    {suggestions_html or "<li>No suggestions available.</li>"}
                </ul>
            </div>
        </div>
        
        <div class="footer">
            <p>MI Learning Platform | Motivational Interviewing Practice Analysis</p>
            <p>This report was generated automatically based on AI analysis of your practice conversation.</p>
        </div>
    </div>
</body>
</html>"""

    return html


@router.post("/report/html", response_class=HTMLResponse)
async def export_analysis_html(
    request: ExportRequest, auth: Optional[AuthContext] = Depends(get_current_user)
):
    """
    Export analysis report as styled HTML.

    Returns HTML that can be viewed in browser or printed to PDF.
    Includes a print button for easy PDF generation.
    """
    try:
        html_content = _generate_html_report(
            analysis=request.analysis, title=request.title
        )

        return HTMLResponse(content=html_content)

    except Exception as e:
        logger.error(f"Failed to generate HTML report: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to generate report: {str(e)}"
        )


@router.get("/report/{analysis_id}/html")
async def export_analysis_by_id_html(
    analysis_id: str, auth: AuthContext = Depends(get_current_user)
):
    """
    Export a saved analysis report as styled HTML.

    Retrieves analysis from database and returns styled HTML.
    """
    try:
        # Import here to avoid circular dependencies
        from app.services.analysis_persistence_service import get_analysis_by_id

        analysis_data = get_analysis_by_id(analysis_id, auth.user_id)

        if not analysis_data:
            raise HTTPException(status_code=404, detail="Analysis not found")

        html_content = _generate_html_report(
            analysis=analysis_data,
            title=f"MI Practice Analysis - {analysis_data.get('persona_name', 'Session')}",
        )

        return HTMLResponse(content=html_content)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate HTML report: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to generate report: {str(e)}"
        )


@router.post("/report/json")
async def export_analysis_json(
    request: ExportRequest, auth: Optional[AuthContext] = Depends(get_current_user)
):
    """
    Export analysis report as JSON.

    Returns the raw analysis data as JSON for programmatic use.
    """
    try:
        return JSONResponse(
            content={
                "title": request.title,
                "generated_at": datetime.utcnow().isoformat(),
                "analysis": request.analysis,
            }
        )

    except Exception as e:
        logger.error(f"Failed to generate JSON report: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to generate report: {str(e)}"
        )
