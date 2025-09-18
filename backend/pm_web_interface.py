"""
HTML File Ingestion Interface for PM Intelligence System - FIXED VERSION

This module provides a web-based interface for file upload and processing
that integrates with the CC_file1.py ingestion engine.

Fixed Issues:
- File input visibility
- JavaScript event handlers
- File display functionality
- Run button enablement

Author: PM Intelligence Team
Version: 1.1.0 (Fixed)
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
    from .CC_file1 import FileIngestionEngine, ProcessingResult
except ImportError:
    try:
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
app = FastAPI(title="PM File Ingestion Interface", version="1.1.0")

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
            
            .upload-section.dragover {
                border-color: #007bff;
                background: #e7f3ff;
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
            
            .file-input-label {
                display: inline-block;
                background: #007bff;
                color: white;
                padding: 12px 30px;
                border-radius: 8px;
                cursor: pointer;
                font-weight: 500;
                transition: all 0.3s ease;
                margin: 10px;
            }
            
            .file-input-label:hover {
                background: #0056b3;
                transform: translateY(-2px);
            }
            
            .selected-files {
                margin-top: 20px;
                max-height: 200px;
                overflow-y: auto;
            }
            
            .file-item {
                background: white;
                padding: 15px;
                margin: 10px 0;
                border-radius: 8px;
                border: 1px solid #dee2e6;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
            
            .file-name {
                font-weight: 500;
                color: #333;
            }
            
            .file-size {
                color: #666;
                font-size: 0.9em;
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
            
            .clear-button:hover {
                background: #c82333;
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
            
            .metric-card.warning {
                border-left-color: #ffc107;
            }
            
            .metric-card.error {
                border-left-color: #dc3545;
            }
            
            .metric-number {
                font-size: 2em;
                font-weight: bold;
                color: #333;
                margin-bottom: 5px;
            }
            
            .metric-label {
                color: #666;
                font-weight: 500;
            }
            
            .progress-bar {
                width: 100%;
                height: 8px;
                background: #e9ecef;
                border-radius: 4px;
                overflow: hidden;
                margin: 20px 0;
            }
            
            .progress-fill {
                height: 100%;
                background: linear-gradient(90deg, #007bff, #28a745);
                width: 0%;
                transition: width 0.5s ease;
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
            
            .next-steps {
                background: linear-gradient(135deg, #e3f2fd, #f3e5f5);
                padding: 25px;
                border-radius: 12px;
                margin-top: 25px;
                border-left: 5px solid #007bff;
            }
            
            .validation-button {
                background: linear-gradient(135deg, #6f42c1, #e83e8c);
                color: white;
                border: none;
                padding: 12px 30px;
                border-radius: 8px;
                cursor: pointer;
                font-weight: 500;
                margin-top: 15px;
                transition: all 0.3s ease;
            }
            
            .validation-button:hover {
                transform: translateY(-2px);
                box-shadow: 0 8px 16px rgba(111, 66, 193, 0.3);
            }

            .file-display {
                margin: 15px 0;
                padding: 15px;
                background: #e7f3ff;
                border: 1px solid #007bff;
                border-radius: 5px;
                display: none;
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
                <div class="progress-bar">
                    <div class="progress-fill" id="progressFill"></div>
                </div>
            </div>
            
            <div class="results-section" id="resultsSection">
                <h2>Processing Results</h2>
                <div class="results-summary" id="resultsSummary"></div>
                <div id="detailedResults"></div>
                
                <div class="next-steps">
                    <h3>Next Steps</h3>
                    <p>Files have been processed and stored. Ready for validation pipeline.</p>
                    <button class="validation-button" onclick="proceedToValidation()">
                        Proceed to Validation →
                    </button>
                </div>
            </div>
        </div>
        
        <script>
            // Global variables
            let selectedFiles = [];
            
            // Initialize when page loads
            document.addEventListener('DOMContentLoaded', function() {
                initializeFileUpload();
            });
            
            function initializeFileUpload() {
                const fileInput = document.getElementById('fileInput');
                const uploadSection = document.getElementById('uploadSection');
                
                // File input change handler
                fileInput.addEventListener('change', handleFileSelect);
                
                // Drag and drop handlers
                uploadSection.addEventListener('dragover', handleDragOver);
                uploadSection.addEventListener('dragleave', handleDragLeave);
                uploadSection.addEventListener('drop', handleDrop);
                
                console.log('✅ File upload system initialized');
            }
            
            function handleFileSelect(event) {
                const files = Array.from(event.target.files);
                selectedFiles = files;
                updateFileDisplay();
                updateRunButton();
                console.log('Files selected:', files.map(f => f.name));
            }
            
            function handleDragOver(e) {
                e.preventDefault();
                e.currentTarget.classList.add('dragover');
            }
            
            function handleDragLeave(e) {
                e.preventDefault();
                e.currentTarget.classList.remove('dragover');
            }
            
            function handleDrop(e) {
                e.preventDefault();
                e.currentTarget.classList.remove('dragover');
                
                const files = Array.from(e.dataTransfer.files);
                selectedFiles = files;
                
                // Update the file input to show the dropped files
                const fileInput = document.getElementById('fileInput');
                fileInput.files = e.dataTransfer.files;
                
                updateFileDisplay();
                updateRunButton();
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
                    runButton.style.background = 'linear-gradient(135deg, #28a745, #20c997)';
                    runButton.style.cursor = 'pointer';
                    runButton.style.opacity = '1';
                } else {
                    runButton.disabled = true;
                    runButton.style.background = '#6c757d';
                    runButton.style.cursor = 'not-allowed';
                    runButton.style.opacity = '0.6';
                }
            }
            
            function clearFiles() {
                selectedFiles = [];
                document.getElementById('fileInput').value = '';
                updateFileDisplay();
                updateRunButton();
                
                // Hide results if showing
                const resultsSection = document.getElementById('resultsSection');
                if (resultsSection) {
                    resultsSection.style.display = 'none';
                }
            }
            
            function formatBytes(bytes) {
                if (bytes === 0) return '0 Bytes';
                const k = 1024;
                const sizes = ['Bytes', 'KB', 'MB', 'GB'];
                const i = Math.floor(Math.log(bytes) / Math.log(k));
                return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
            }
            
            async function processFiles() {
                if (selectedFiles.length === 0) {
                    alert('Please select files first');
                    return;
                }
                
                console.log('🚀 Processing files:', selectedFiles.map(f => f.name));
                
                // Show loading
                const loadingSection = document.getElementById('loadingSection');
                const resultsSection = document.getElementById('resultsSection');
                loadingSection.style.display = 'block';
                resultsSection.style.display = 'none';
                
                // Animate progress bar
                const progressFill = document.getElementById('progressFill');
                let progress = 0;
                const progressInterval = setInterval(() => {
                    progress += 2;
                    progressFill.style.width = progress + '%';
                    if (progress >= 90) clearInterval(progressInterval);
                }, 100);
                
                try {
                    // Upload files
                    const formData = new FormData();
                    selectedFiles.forEach(file => {
                        formData.append('files', file);
                    });
                    
                    const uploadResponse = await fetch('/upload-files', {
                        method: 'POST',
                        body: formData
                    });
                    
                    if (!uploadResponse.ok) {
                        throw new Error('File upload failed');
                    }
                    
                    const uploadResult = await uploadResponse.json();
                    console.log('Upload result:', uploadResult);
                    
                    // Process files
                    const processResponse = await fetch('/process-files', {
                        method: 'POST'
                    });
                    
                    const processResult = await processResponse.json();
                    console.log('Process result:', processResult);
                    
                    // Complete progress
                    progressFill.style.width = '100%';
                    
                    // Show results
                    setTimeout(() => {
                        loadingSection.style.display = 'none';
                        displayResults(processResult);
                    }, 500);
                    
                } catch (error) {
                    console.error('Processing failed:', error);
                    loadingSection.style.display = 'none';
                    alert('Processing failed: ' + error.message);
                }
            }
            
            function displayResults(results) {
                const resultsSection = document.getElementById('resultsSection');
                const summaryContainer = document.getElementById('resultsSummary');
                
                // Create summary cards
                summaryContainer.innerHTML = `
                    <div class="metric-card">
                        <div class="metric-number">${results.total_files || 0}</div>
                        <div class="metric-label">Total Files</div>
                    </div>
                    <div class="metric-card success">
                        <div class="metric-number">${results.successful_processes || 0}</div>
                        <div class="metric-label">Successful</div>
                    </div>
                    <div class="metric-card error">
                        <div class="metric-number">${results.failed_processes || 0}</div>
                        <div class="metric-label">Failed</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-number">${results.success_rate || 0}%</div>
                        <div class="metric-label">Success Rate</div>
                    </div>
                `;
                
                resultsSection.style.display = 'block';
                
                // Clear selected files
                clearFiles();
            }
            
            function proceedToValidation() {
                alert('Proceeding to validation pipeline...\\n\\nThis would navigate to the next step where processed data is validated and analyzed.');
                // In production, this would navigate to the validation interface
                window.location.href = '/validation';
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
