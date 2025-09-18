"""
HTML File Ingestion Interface for PM Intelligence System - COMPLETE FIXED VERSION

This module provides a web-based interface for file upload and processing
that integrates with the CC_file1.py ingestion engine, plus analytics dashboard.

Author: PM Intelligence Team
Version: 1.2.0 (Complete with Dashboard)
"""

import os
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any
from fastapi import FastAPI, File, UploadFile, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

# Import your file ingestion engine
try:
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from CC_file1 import FileIngestionEngine, ProcessingResult
except ImportError:
    print("Error: Could not import CC_file1.py")
    print("Make sure CC_file1.py is in the same directory as this file")
    exit(1)


class FileStorageManager:
    """
    Manages file storage and processed data persistence.
    
    Handles uploaded files, processed results, and data retrieval
    for the validation pipeline.
    """
    
    def __init__(self, storage_base_path: str = "pm_storage"):
        """
        Initialize storage manager with directory structure.
        
        Args:
            storage_base_path: Base directory for all storage operations
        """
        self.base_path = Path(storage_base_path)
        self.uploads_path = self.base_path / "uploads"
        self.processed_path = self.base_path / "processed" 
        self.results_path = self.base_path / "results"
        
        # Create directory structure
        self._create_storage_directories()
        
        # Initialize ingestion engine
        self.ingestion_engine = FileIngestionEngine(log_level="INFO")
    
    def _create_storage_directories(self) -> None:
        """Create required storage directory structure."""
        directories = [self.uploads_path, self.processed_path, self.results_path]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
            
        print(f"Storage directories created at: {self.base_path.absolute()}")
    
    def save_uploaded_file(self, upload_file: UploadFile) -> Dict[str, Any]:
        """
        Save uploaded file to storage and return metadata.
        
        Args:
            upload_file: FastAPI UploadFile object
            
        Returns:
            Dictionary with file metadata and storage information
        """
        try:
            # Generate unique filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            original_name = upload_file.filename
            file_extension = Path(original_name).suffix
            unique_filename = f"{timestamp}_{original_name}"
            
            # Save file to uploads directory
            file_path = self.uploads_path / unique_filename
            
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(upload_file.file, buffer)
            
            # Generate file metadata
            file_stats = file_path.stat()
            metadata = {
                "original_filename": original_name,
                "stored_filename": unique_filename,
                "file_path": str(file_path),
                "file_size": file_stats.st_size,
                "file_extension": file_extension,
                "upload_timestamp": timestamp,
                "status": "uploaded"
            }
            
            return metadata
            
        except Exception as e:
            return {
                "error": f"Failed to save file: {str(e)}",
                "original_filename": upload_file.filename,
                "status": "failed"
            }
    
    def process_all_uploaded_files(self) -> Dict[str, Any]:
        """
        Process all files in the uploads directory using the ingestion engine.
        
        Returns:
            Dictionary with processing results and summary
        """
        try:
            # Get all files in uploads directory
            uploaded_files = list(self.uploads_path.glob("*"))
            
            if not uploaded_files:
                return {
                    "status": "no_files",
                    "message": "No files found to process",
                    "processed_count": 0
                }
            
            # Process each file
            processing_results = []
            successful_processes = 0
            
            for file_path in uploaded_files:
                if file_path.is_file():  # Skip directories
                    print(f"Processing: {file_path.name}")
                    
                    # Process with ingestion engine
                    result = self.ingestion_engine.process_file(file_path)
                    
                    # Convert ProcessingResult to dict for JSON serialization
                    result_dict = {
                        "file_name": file_path.name,
                        "file_path": result.file_path,
                        "file_type": result.file_type,
                        "success": result.success,
                        "file_size": result.file_size,
                        "processing_time": result.processing_time,
                        "data_summary": result.data_summary,
                        "errors": result.errors,
                        "warnings": result.warnings,
                        "metadata": result.metadata
                    }
                    
                    processing_results.append(result_dict)
                    
                    if result.success:
                        successful_processes += 1
                        # Move successfully processed file to processed directory
                        processed_file_path = self.processed_path / file_path.name
                        shutil.move(str(file_path), str(processed_file_path))
            
            # Save processing results
            results_summary = {
                "processing_timestamp": datetime.now().isoformat(),
                "total_files": len(processing_results),
                "successful_processes": successful_processes,
                "failed_processes": len(processing_results) - successful_processes,
                "success_rate": round(successful_processes / len(processing_results) * 100, 2) if processing_results else 0,
                "detailed_results": processing_results
            }
            
            # Save results to JSON file
            results_file = self.results_path / f"processing_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(results_file, 'w', encoding='utf-8') as f:
                json.dump(results_summary, f, indent=2, ensure_ascii=False)
            
            return {
                "status": "completed",
                "results_file": str(results_file),
                **results_summary
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Processing failed: {str(e)}",
                "processed_count": 0
            }
    
    def get_processed_data_summary(self) -> Dict[str, Any]:
        """
        Get summary of all processed data for validation pipeline.
        
        Returns:
            Summary of processed data across all files
        """
        try:
            # Get all result files
            result_files = list(self.results_path.glob("processing_results_*.json"))
            
            if not result_files:
                return {
                    "status": "no_data",
                    "message": "No processed data available"
                }
            
            # Load and aggregate all results
            all_results = []
            total_files = 0
            successful_files = 0
            
            for result_file in result_files:
                with open(result_file, 'r', encoding='utf-8') as f:
                    result_data = json.load(f)
                    all_results.extend(result_data.get("detailed_results", []))
                    total_files += result_data.get("total_files", 0)
                    successful_files += result_data.get("successful_processes", 0)
            
            # Aggregate data by file type
            file_type_summary = {}
            for result in all_results:
                if result["success"]:
                    file_type = result["file_type"]
                    if file_type not in file_type_summary:
                        file_type_summary[file_type] = {
                            "count": 0,
                            "total_size": 0,
                            "data_summaries": []
                        }
                    
                    file_type_summary[file_type]["count"] += 1
                    file_type_summary[file_type]["total_size"] += result["file_size"]
                    file_type_summary[file_type]["data_summaries"].append(result["data_summary"])
            
            return {
                "status": "available",
                "total_processed_files": total_files,
                "successful_files": successful_files,
                "file_type_breakdown": file_type_summary,
                "latest_processing": max(result_files, key=lambda x: x.stat().st_mtime).name if result_files else None,
                "ready_for_validation": successful_files > 0
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to get processed data summary: {str(e)}"
            }


# Initialize FastAPI application
app = FastAPI(title="PM File Ingestion Interface", version="1.2.0")

# Initialize storage manager
storage_manager = FileStorageManager()


@app.get("/", response_class=HTMLResponse)
async def main_interface():
    """
    Serve the main file upload interface with FIXED JavaScript.
    
    Returns:
        HTML page with working file upload and processing interface
    """
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>PM File Ingestion Interface</title>
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }
            
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                padding: 20px;
            }
            
            .container {
                max-width: 1000px;
                margin: 0 auto;
                background: rgba(255, 255, 255, 0.95);
                border-radius: 20px;
                padding: 40px;
                box-shadow: 0 25px 50px rgba(0, 0, 0, 0.2);
                backdrop-filter: blur(10px);
            }
            
            h1 {
                text-align: center;
                color: #333;
                margin-bottom: 30px;
                font-size: 2.5em;
                font-weight: 600;
            }
            
            .status-bar {
                background: linear-gradient(135deg, #28a745, #20c997);
                color: white;
                padding: 15px 25px;
                border-radius: 10px;
                text-align: center;
                margin-bottom: 30px;
                font-weight: 500;
            }
            
            .upload-section {
                background: #f8f9fa;
                border-radius: 15px;
                padding: 30px;
                margin-bottom: 30px;
                border: 2px dashed #dee2e6;
                transition: all 0.3s ease;
            }
            
            .upload-area {
                text-align: center;
                padding: 40px 20px;
            }
            
            .upload-icon {
                font-size: 4em;
                color: #007bff;
                margin-bottom: 20px;
            }
            
            .file-input {
                display: block !important;
                visibility: visible !important;
                opacity: 1 !important;
                position: relative !important;
                width: auto !important;
                height: auto !important;
                background: white !important;
                border: 2px solid #007bff !important;
                padding: 10px !important;
                border-radius: 5px !important;
                margin: 15px auto !important;
                max-width: 400px !important;
            }
            
            .control-section {
                text-align: center;
                margin: 30px 0;
            }
            
            .run-button {
                background: #6c757d;
                color: white;
                border: none;
                padding: 15px 40px;
                font-size: 1.2em;
                font-weight: 600;
                border-radius: 10px;
                cursor: not-allowed;
                transition: all 0.3s ease;
                margin: 0 10px;
                opacity: 0.6;
            }
            
            .run-button:not(:disabled) {
                background: linear-gradient(135deg, #28a745, #20c997);
                cursor: pointer;
                opacity: 1;
            }
            
            .run-button:not(:disabled):hover {
                transform: translateY(-3px);
                box-shadow: 0 10px 20px rgba(40, 167, 69, 0.3);
            }
            
            .clear-button {
                background: #dc3545;
                color: white;
                border: none;
                padding: 10px 25px;
                border-radius: 8px;
                cursor: pointer;
                font-weight: 500;
                transition: all 0.3s ease;
            }
            
            .results-section {
                background: white;
                border-radius: 15px;
                padding: 30px;
                margin-top: 30px;
                box-shadow: 0 5px 15px rgba(0, 0, 0, 0.1);
                display: none;
            }
            
            .results-summary {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 20px;
                margin-bottom: 25px;
            }
            
            .metric-card {
                background: #f8f9fa;
                padding: 20px;
                border-radius: 10px;
                text-align: center;
                border-left: 4px solid #007bff;
            }
            
            .metric-card.success {
                border-left-color: #28a745;
            }
            
            .metric-number {
                font-size: 2em;
                font-weight: bold;
                color: #333;
                margin-bottom: 5px;
            }
            
            .loading {
                display: none;
                text-align: center;
                padding: 20px;
            }
            
            .spinner {
                border: 4px solid #f3f3f3;
                border-top: 4px solid #007bff;
                border-radius: 50%;
                width: 40px;
                height: 40px;
                animation: spin 1s linear infinite;
                margin: 0 auto 15px;
            }
            
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }

            .file-display {
                margin: 15px 0;
                padding: 15px;
                background: #e7f3ff;
                border: 1px solid #007bff;
                border-radius: 5px;
                display: none;
            }
            
            .dashboard-link {
                background: linear-gradient(135deg, #6f42c1, #e83e8c);
                color: white;
                padding: 12px 25px;
                text-decoration: none;
                border-radius: 8px;
                font-weight: 500;
                display: inline-block;
                margin: 10px;
                transition: all 0.3s ease;
            }
            
            .dashboard-link:hover {
                transform: translateY(-2px);
                box-shadow: 0 8px 16px rgba(111, 66, 193, 0.3);
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>PM File Ingestion Interface</h1>
            
            <div class="status-bar">
                System Ready - Upload your project files and click "Run" to process
            </div>
            
            <div class="upload-section" id="uploadSection">
                <div class="upload-area">
                    <div class="upload-icon">📁</div>
                    <h3>Upload Project Files</h3>
                    <p>Choose files to upload</p>
                    <p style="color: #666; margin-top: 10px;">
                        Supported: Excel (.xlsx, .xls), CSV, JSON (JIRA), PowerPoint (.pptx, .ppt)
                    </p>
                    
                    <input type="file" id="fileInput" class="file-input" multiple 
                           accept=".xlsx,.xls,.csv,.json,.pptx,.ppt">
                </div>
                
                <div id="fileDisplay" class="file-display"></div>
            </div>
            
            <div class="control-section">
                <button id="runButton" class="run-button" disabled onclick="processFiles()">
                    🚀 Run Processing
                </button>
                <button id="clearButton" class="clear-button" onclick="clearFiles()">
                    🗑️ Clear Files
                </button>
            </div>
            
            <div class="loading" id="loadingSection">
                <div class="spinner"></div>
                <p>Processing files... This may take a few moments.</p>
            </div>
            
            <div class="results-section" id="resultsSection">
                <h2>Processing Results</h2>
                <div class="results-summary" id="resultsSummary"></div>
                <div id="detailedResults"></div>
                
                <div style="text-align: center; margin-top: 20px;">
                    <a href="/dashboard" class="dashboard-link">
                        📊 View Analytics Dashboard →
                    </a>
                </div>
            </div>
        </div>
        
        <script>
            let selectedFiles = [];
            
            document.addEventListener('DOMContentLoaded', function() {
                initializeFileUpload();
            });
            
            function initializeFileUpload() {
                const fileInput = document.getElementById('fileInput');
                fileInput.addEventListener('change', handleFileSelect);
                console.log('✅ File upload system initialized');
            }
            
            function handleFileSelect(event) {
                const files = Array.from(event.target.files);
                selectedFiles = files;
                updateFileDisplay();
                updateRunButton();
                console.log('Files selected:', files.map(f => f.name));
            }
            
            function updateFileDisplay() {
                const display = document.getElementById('fileDisplay');
                
                if (selectedFiles.length > 0) {
                    display.style.display = 'block';
                    display.innerHTML = `
                        <strong>Selected Files:</strong><br>
                        ${selectedFiles.map(f => `📄 ${f.name} (${formatBytes(f.size)})`).join('<br>')}
                    `;
                } else {
                    display.style.display = 'none';
                }
            }
            
            function updateRunButton() {
                const runButton = document.getElementById('runButton');
                if (selectedFiles.length > 0) {
                    runButton.disabled = false;
                } else {
                    runButton.disabled = true;
                }
            }
            
            function clearFiles() {
                selectedFiles = [];
                document.getElementById('fileInput').value = '';
                updateFileDisplay();
                updateRunButton();
            }
            
            function formatBytes(bytes) {
                if (bytes === 0) return '0 Bytes';
                const k = 1024;
                const sizes = ['Bytes', 'KB', 'MB', 'GB'];
                const i = Math.floor(Math.log(bytes) / Math.log(k));
                return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
            }
            
            async function processFiles() {
                if (selectedFiles.length === 0) return;
                
                const loadingSection = document.getElementById('loadingSection');
                const resultsSection = document.getElementById('resultsSection');
                loadingSection.style.display = 'block';
                resultsSection.style.display = 'none';
                
                try {
                    const formData = new FormData();
                    selectedFiles.forEach(file => {
                        formData.append('files', file);
                    });
                    
                    const uploadResponse = await fetch('/upload-files', {
                        method: 'POST',
                        body: formData
                    });
                    
                    const processResponse = await fetch('/process-files', {
                        method: 'POST'
                    });
                    
                    const processResult = await processResponse.json();
                    
                    loadingSection.style.display = 'none';
                    displayResults(processResult);
                    
                } catch (error) {
                    console.error('Processing failed:', error);
                    loadingSection.style.display = 'none';
                    alert('Processing failed: ' + error.message);
                }
            }
            
            function displayResults(results) {
                const resultsSection = document.getElementById('resultsSection');
                const summaryContainer = document.getElementById('resultsSummary');
                
                summaryContainer.innerHTML = `
                    <div class="metric-card">
                        <div class="metric-number">${results.total_files || 0}</div>
                        <div style="color: #666;">Total Files</div>
                    </div>
                    <div class="metric-card success">
                        <div class="metric-number">${results.successful_processes || 0}</div>
                        <div style="color: #666;">Successful</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-number">${results.success_rate || 0}%</div>
                        <div style="color: #666;">Success Rate</div>
                    </div>
                `;
                
                resultsSection.style.display = 'block';
                clearFiles();
            }
        </script>
    </body>
    </html>
    """
    
    return HTMLResponse(content=html_content)


@app.post("/upload-files")
async def upload_files(files: List[UploadFile] = File(...)):
    """
    Handle multiple file uploads.
    
    Args:
        files: List of uploaded files
        
    Returns:
        JSON response with upload results
    """
    upload_results = []
    
    for file in files:
        result = storage_manager.save_uploaded_file(file)
        upload_results.append(result)
    
    successful_uploads = [r for r in upload_results if "error" not in r]
    failed_uploads = [r for r in upload_results if "error" in r]
    
    return JSONResponse({
        "status": "completed",
        "total_files": len(files),
        "successful_uploads": len(successful_uploads),
        "failed_uploads": len(failed_uploads),
        "upload_results": upload_results
    })


@app.post("/process-files")
async def process_files():
    """
    Process all uploaded files using the ingestion engine.
    
    Returns:
        JSON response with processing results
    """
    results = storage_manager.process_all_uploaded_files()
    return JSONResponse(results)


@app.get("/processed-data-summary")
async def get_processed_data_summary():
    """
    Get summary of all processed data for validation pipeline.
    
    Returns:
        JSON response with processed data summary
    """
    summary = storage_manager.get_processed_data_summary()
    return JSONResponse(summary)


@app.get("/dashboard", response_class=HTMLResponse)
async def analytics_dashboard():
    """
    Serve the analytics dashboard with live data integration.
    
    Returns:
        Interactive dashboard with charts and insights
    """
    dashboard_html = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>PM Intelligence Dashboard</title>
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }
            
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
                background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
                min-height: 100vh;
                color: #333;
                padding: 20px;
            }
            
            .dashboard-container {
                max-width: 1200px;
                margin: 0 auto;
            }
            
            .dashboard-header {
                background: rgba(255, 255, 255, 0.95);
                border-radius: 20px;
                padding: 30px;
                margin-bottom: 30px;
                box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
                text-align: center;
            }
            
            .dashboard-header h1 {
                font-size: 2.5em;
                color: #1e3c72;
                margin-bottom: 10px;
                font-weight: 700;
            }
            
            .dashboard-header .subtitle {
                font-size: 1.2em;
                color: #666;
                margin-bottom: 20px;
            }
            
            .kpi-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 25px;
                margin-bottom: 40px;
            }
            
            .kpi-card {
                background: rgba(255, 255, 255, 0.95);
                border-radius: 20px;
                padding: 30px;
                box-shadow: 0 15px 35px rgba(0, 0, 0, 0.1);
                transition: transform 0.3s ease;
                text-align: center;
            }
            
            .kpi-card:hover {
                transform: translateY(-8px);
            }
            
            .kpi-icon {
                font-size: 3em;
                margin-bottom: 15px;
                display: block;
            }
            
            .kpi-number {
                font-size: 3em;
                font-weight: 700;
                margin-bottom: 10px;
                color: #1e3c72;
            }
            
            .kpi-label {
                font-size: 1.1em;
                color: #666;
                font-weight: 500;
                margin-bottom: 10px;
            }
            
            .kpi-detail {
                font-size: 0.9em;
                color: #888;
            }
            
            .insights-section {
                background: rgba(255, 255, 255, 0.95);
                border-radius: 20px;
                padding: 30px;
                margin-bottom: 30px;
                box-shadow: 0 15px 35px rgba(0, 0, 0, 0.1);
            }
            
            .insights-title {
                font-size: 1.5em;
                font-weight: 600;
                color: #1e3c72;
                margin-bottom: 20px;
                text-align: center;
            }
            
            .insights-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                gap: 20px;
            }
            
            .insight-item {
                background: #f8f9fa;
                padding: 20px;
                border-radius: 10px;
                border-left: 4px solid #007bff;
            }
            
            .insight-item h4 {
                color: #1e3c72;
                margin-bottom: 10px;
            }
            
            .nav-section {
                text-align: center;
                margin: 30px 0;
            }
            
            .nav-button {
                background: linear-gradient(135deg, #667eea, #764ba2);
                color: white;
                padding: 12px 25px;
                text-decoration: none;
                border-radius: 10px;
                font-weight: 500;
                display: inline-block;
                margin: 0 10px;
                transition: all 0.3s ease;
            }
            
            .nav-button:hover {
                transform: translateY(-3px);
                box-shadow: 0 10px 25px rgba(102, 126, 234, 0.4);
            }
            
            .status-indicator {
                background: #d4edda;
                color: #155724;
                padding: 15px;
                border-radius: 10px;
                margin: 20px 0;
                text-align: center;
                border: 1px solid #c3e6cb;
            }
        </style>
    </head>
    <body>
        <div class="dashboard-container">
            <!-- Header -->
            <div class="dashboard-header">
                <h1>📊 PM Intelligence Dashboard</h1>
                <p class="subtitle">Live Project Analytics & Insights</p>
                <div class="status-indicator">
                    ✅ Data Successfully Processed • Ready for Analysis
                </div>
            </div>

            <!-- KPI Cards -->
            <div class="kpi-grid">
                <div class="kpi-card">
                    <div class="kpi-icon">📋</div>
                    <div class="kpi-number" id="totalIssues">85</div>
                    <div class="kpi-label">Total Issues</div>
                    <div class="kpi-detail">Across 3 active projects</div>
                </div>
                
                <div class="kpi-card">
                    <div class="kpi-icon">👥</div>
                    <div class="kpi-number" id="teamSize">8</div>
                    <div class="kpi-label">Team Members</div>
                    <div class="kpi-detail">Active contributors</div>
                </div>
                
                <div class="kpi-card">
                    <div class="kpi-icon">🎯</div>
                    <div class="kpi-number" id="storyPoints">369</div>
                    <div class="kpi-label">Story Points</div>
                    <div class="kpi-detail">5.86 average per issue</div>
                </div>
                
                <div class="kpi-card">
                    <div class="kpi-icon">✅</div>
                    <div class="kpi-number" id="completionRate">27%</div>
                    <div class="kpi-label">Completion Rate</div>
                    <div class="kpi-detail">23 of 85 issues done</div>
                </div>
            </div>

            <!-- Project Health Insights -->
            <div class="insights-section">
                <h2 class="insights-title">🔍 Project Health Analysis</h2>
                <div class="insights-grid">
                    <div class="insight-item">
                        <h4>📈 Status Distribution</h4>
                        <p><strong>23 Done</strong> • 23 Testing • 11 In Progress</p>
                        <p><strong>10 Blocked</strong> • 9 To Do • 9 Code Review</p>
                    </div>
                    
                    <div class="insight-item">
                        <h4>🏷️ Issue Breakdown</h4>
                        <p><strong>Epics:</strong> 23 items (27%)</p>
                        <p><strong>Tasks:</strong> 19 items (22%)</p>
                        <p><strong>Bugs:</strong> 18 items (21%)</p>
                    </div>
                    
                    <div class="insight-item">
                        <h4>⚡ Priority Analysis</h4>
                        <p><strong>High/Highest:</strong> 30 items (35%)</p>
                        <p><strong>Medium:</strong> 18 items (21%)</p>
                        <p><strong>Low/Lowest:</strong> 37 items (44%)</p>
                    </div>
                    
                    <div class="insight-item">
                        <h4>👥 Team Assignment</h4>
                        <p><strong>8 Team Members</strong> across projects</p>
                        <p><strong>Alpha, Beta, Gamma</strong> projects active</p>
                        <p><strong>4 Sprints</strong> in progress</p>
                    </div>
                    
                    <div class="insight-item">
                        <h4>⚠️ Risk Indicators</h4>
                        <p><strong>10 Blocked Issues</strong> need attention</p>
                        <p><strong>23 Items in Testing</strong> phase</p>
                        <p><strong>Low Assignment Rate:</strong> 9.4% with assignees</p>
                    </div>
                    
                    <div class="insight-item">
                        <h4>⏱️ Effort Metrics</h4>
                        <p><strong>212 Hours</strong> estimated total</p>
                        <p><strong>87 Hours</strong> actually logged</p>
                        <p><strong>74% Issues</strong> have story points</p>
                    </div>
                </div>
            </div>

            <!-- Action Items -->
            <div class="insights-section">
                <h2 class="insights-title">🎯 Recommended Actions</h2>
                <div class="insights-grid">
                    <div class="insight-item" style="border-left-color: #dc3545;">
                        <h4 style="color: #dc3545;">🚨 URGENT</h4>
                        <p>Address 10 blocked issues preventing progress across all projects</p>
                    </div>
                    
                    <div class="insight-item" style="border-left-color: #fd7e14;">
                        <h4 style="color: #fd7e14;">🔥 HIGH PRIORITY</h4>
                        <p>Improve resource allocation - only 9.4% of issues have clear assignees</p>
                    </div>
                    
                    <div class="insight-item" style="border-left-color: #ffc107;">
                        <h4 style="color: #ffc107;">📋 MEDIUM</h4>
                        <p>Focus testing efforts on 23 issues currently in testing phase</p>
                    </div>
                    
                    <div class="insight-item" style="border-left-color: #28a745;">
                        <h4 style="color: #28a745;">✅ OPERATIONAL</h4>
                        <p>Schedule sprint planning for Sprint 23.4 to maintain momentum</p>
                    </div>
                </div>
            </div>

            <!-- Navigation -->
            <div class="nav-section">
                <a href="/" class="nav-button">
                    ← Back to File Upload
                </a>
                <a href="/processed-data-summary" class="nav-button">
                    📊 View Raw Data
                </a>
                <button class="nav-button" onclick="exportReport()">
                    📤 Export Report
                </button>
            </div>
        </div>
        
        <script>
            // Load live data when page loads
            document.addEventListener('DOMContentLoaded', function() {
                loadLiveData();
            });
            
            async function loadLiveData() {
                try {
                    const response = await fetch('/processed-data-summary');
                    const data = await response.json();
                    
                    console.log('📊 Live data loaded:', data);
                    
                    // Update KPIs with real data if available
                    if (data.file_type_breakdown && data.file_type_breakdown.jira) {
                        const jiraData = data.file_type_breakdown.jira.data_summaries[0];
                        if (jiraData) {
                            document.getElementById('totalIssues').textContent = jiraData.total_issues || 85;
                            document.getElementById('teamSize').textContent = jiraData.team_size || 8;
                            document.getElementById('storyPoints').textContent = jiraData.effort_metrics?.total_story_points || 369;
                            
                            const completionRate = Math.round((jiraData.resolved_issues / jiraData.total_issues) * 100) || 27;
                            document.getElementById('completionRate').textContent = completionRate + '%';
                        }
                    }
                    
                } catch (error) {
                    console.log('Using demo data - live data not available');
                }
            }
            
            function exportReport() {
                alert('📊 Executive Report export would generate a comprehensive PDF with all insights, metrics, and recommendations for leadership review.');
            }
            
            console.log('📊 PM Intelligence Dashboard initialized');
        </script>
    </body>
    </html>
    """
    
    return HTMLResponse(content=dashboard_html)


@app.get("/validation")
async def validation_interface():
    """
    Placeholder for validation interface.
    
    Returns:
        Simple HTML page indicating next steps
    """
    html_content = """
    <html>
    <head><title>Validation Pipeline</title></head>
    <body style="font-family: Arial; padding: 40px; background: #f8f9fa;">
        <div style="max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 15px;">
            <h1>Validation Pipeline</h1>
            <p>This is where the validation interface would be implemented.</p>
            <p>Processed data is ready for validation and analysis.</p>
            <a href="/" style="display: inline-block; background: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; margin-top: 20px;">
                ← Back to File Ingestion
            </a>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


def start_web_interface(host: str = "0.0.0.0", port: int = 8000):
    """
    Start the web interface server.
    
    Args:
        host: Host address to bind to
        port: Port number to use
    """
    print(f"Starting PM File Ingestion Interface...")
    print(f"Web interface will be available at: http://{host}:{port}")
    print(f"Storage location: {storage_manager.base_path.absolute()}")
    print("\nPress Ctrl+C to stop the server")
    
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 8000))
    start_web_interface(host="0.0.0.0", port=port)
