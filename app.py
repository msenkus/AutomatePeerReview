#!/usr/bin/env python3
"""
Web-based Team Evaluation Interface
FastAPI app with Selenium automation backend
"""

from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import uvicorn
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import time
import json
import logging
from typing import Optional, List
from pydantic import BaseModel
import threading
import os

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(title="Team Evaluation Assistant")

# Templates directory
templates = Jinja2Templates(directory="templates")

# Global bot instance
evaluation_bot = None


class EvaluationData(BaseModel):
    member_name: str
    score: int
    comments: str


class ConstantData(BaseModel):
    my_name: str
    my_email: str
    milestone: str
    week: str
    my_team: str
    form_url: str


class EvaluationBot:
    def __init__(self):
        self.driver = None
        self.wait = None
        self.constants = {}
        self.current_form_open = False

    def setup_driver(self):
        """Initialize Chrome driver"""
        if self.driver is None:
            chrome_options = Options()
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--window-size=1920,1080')
            # Keep browser visible for user verification

            self.driver = webdriver.Chrome(options=chrome_options)
            self.wait = WebDriverWait(self.driver, 10)
            logger.info("Browser initialized")

    def set_constants(self, constants: dict):
        """Store constant evaluation data"""
        self.constants = constants
        logger.info(f"Constants set for {constants.get('my_name')}")

    def open_form(self):
        """Open a fresh evaluation form"""
        if not self.driver:
            self.setup_driver()

        form_url = self.constants.get('form_url')
        if not form_url:
            raise Exception("Form URL not set in constants")

        logger.info("Opening evaluation form...")
        self.driver.get(form_url)
        time.sleep(3)
        self.current_form_open = True

    def fill_constants(self):
        """Fill the constant fields (name, email, milestone, week, team)"""
        if not self.current_form_open:
            self.open_form()

        try:
            # Fill text fields
            text_inputs = self.driver.find_elements(By.CSS_SELECTOR, "input[type='text']")
            visible_inputs = [inp for inp in text_inputs if inp.is_displayed() and inp.is_enabled()]

            # Fill name and email
            if len(visible_inputs) >= 1:
                visible_inputs[0].clear()
                visible_inputs[0].send_keys(self.constants['my_name'])

            if len(visible_inputs) >= 2:
                visible_inputs[1].clear()
                visible_inputs[1].send_keys(self.constants['my_email'])

            time.sleep(1)

            # Fill radio buttons for constants
            self._select_radio("Milestone", self.constants['milestone'])
            self._select_radio("Week", self.constants['week'])
            self._select_radio("Your team", self.constants['my_team'])

            logger.info("Constant fields filled")
            return True

        except Exception as e:
            logger.error(f"Error filling constants: {str(e)}")
            return False

    def _check_browser_status(self):
        """Check if browser is still available"""
        try:
            # Try to get current URL to test if browser is alive
            self.driver.current_url
            return True
        except:
            logger.warning("Browser window appears to be closed")
            self.driver = None
            self.current_form_open = False
            return False

    def fill_evaluation_data(self, member_name: str, score: int, comments: str):
        """Fill the variable evaluation data with browser status checking"""
        try:
            # Check if browser is still available
            if not self._check_browser_status():
                return False

            # Select team member
            if not self._select_radio("Evaluated Team Member", member_name):
                logger.error("Failed to select team member")
                return False

            # Fill score
            text_inputs = self.driver.find_elements(By.CSS_SELECTOR, "input[type='text']")
            visible_inputs = [inp for inp in text_inputs if inp.is_displayed() and inp.is_enabled()]

            if len(visible_inputs) >= 3:
                visible_inputs[2].clear()
                visible_inputs[2].send_keys(str(score))
                logger.info(f"Filled score: {score}")
            else:
                logger.error("Could not find score field")
                return False

            # Fill comments
            if not self._fill_comments(comments):
                logger.error("Failed to fill comments")
                return False

            logger.info(f"Evaluation data filled for {member_name}")
            return True

        except Exception as e:
            logger.error(f"Error filling evaluation data: {str(e)}")
            # Reset driver if there's an error
            self.driver = None
            self.current_form_open = False
            return False

    def _select_radio(self, question_text: str, choice_text: str):
        """Select a radio button with improved error handling"""
        try:
            # Try multiple question text variations
            question_variations = [
                f"//span[contains(text(), '{question_text}')]/ancestor::div[@role='listitem']",
                f"//span[text()='{question_text}']/ancestor::div[@role='listitem']",
                f"//span[starts-with(text(), '{question_text}')]/ancestor::div[@role='listitem']"
            ]

            question_container = None
            for variation in question_variations:
                containers = self.driver.find_elements(By.XPATH, variation)
                if containers:
                    question_container = containers[0]
                    break

            if not question_container:
                logger.error(f"Could not find question container for: {question_text}")
                return False

            # Try to find and click the choice
            choice_elements = question_container.find_elements(
                By.XPATH,
                f".//span[contains(text(), '{choice_text}')]"
            )

            if choice_elements:
                choice_elements[0].click()
                time.sleep(0.5)
                logger.info(f"Selected '{choice_text}' for '{question_text}'")
                return True
            else:
                logger.error(f"Could not find choice '{choice_text}' for question '{question_text}'")
                return False

        except Exception as e:
            logger.error(f"Error selecting radio button: {str(e)}")
            return False

    def _fill_comments(self, comments: str):
        """Fill comments textarea with error handling"""
        try:
            if not self._check_browser_status():
                return False

            comments_containers = self.driver.find_elements(
                By.XPATH,
                "//span[contains(text(), 'Comments')]/ancestor::div[@role='listitem']"
            )

            if comments_containers:
                textarea = comments_containers[0].find_element(By.CSS_SELECTOR, "textarea")
                textarea.clear()
                textarea.send_keys(comments)
                logger.info(f"Comments filled: {comments[:50]}...")
                return True
            else:
                logger.error("Comments field not found")
                return False

        except Exception as e:
            logger.error(f"Error filling comments: {str(e)}")
            return False

    def submit_form(self):
        """Submit the current form with error handling"""
        try:
            if not self._check_browser_status():
                return False

            submit_button = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, "//span[text()='Submit']/parent::*"))
            )
            submit_button.click()
            time.sleep(3)
            self.current_form_open = False
            logger.info("Form submitted successfully")
            return True

        except Exception as e:
            logger.error(f"Error submitting form: {str(e)}")
            self.current_form_open = False
            return False

    def close(self):
        """Close the browser"""
        if self.driver:
            self.driver.quit()
            self.driver = None
            logger.info("Browser closed")


@app.on_event("startup")
async def startup_event():
    """Initialize the evaluation bot on startup"""
    global evaluation_bot
    evaluation_bot = EvaluationBot()


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up on shutdown"""
    global evaluation_bot
    if evaluation_bot:
        evaluation_bot.close()


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Home page - setup constants"""
    return templates.TemplateResponse("home.html", {"request": request})


@app.post("/setup")
async def setup_constants(
        my_name: str = Form(...),
        my_email: str = Form(...),
        milestone: str = Form(...),
        week: str = Form(...),
        my_team: str = Form(...),
        form_url: str = Form(...)
):
    """Set up constant values"""
    constants = {
        "my_name": my_name,
        "my_email": my_email,
        "milestone": milestone,
        "week": week,
        "my_team": my_team,
        "form_url": form_url
    }

    evaluation_bot.set_constants(constants)
    return RedirectResponse(url="/evaluate", status_code=303)


@app.get("/evaluate", response_class=HTMLResponse)
async def evaluate_page(request: Request):
    """Evaluation page"""
    if not evaluation_bot.constants:
        return RedirectResponse(url="/", status_code=303)

    return templates.TemplateResponse("evaluate.html", {
        "request": request,
        "constants": evaluation_bot.constants
    })


@app.post("/start_evaluation")
async def start_evaluation():
    """Open form and fill constant fields"""
    try:
        if not evaluation_bot.constants:
            return {"status": "error", "message": "Constants not set. Please go back to setup."}

        evaluation_bot.open_form()
        success = evaluation_bot.fill_constants()

        if success:
            return {"status": "success", "message": "Form opened and constants filled"}
        else:
            return {"status": "error", "message": "Failed to fill constants. Please check the browser window."}

    except Exception as e:
        logger.error(f"Error in start_evaluation: {str(e)}")
        return {"status": "error", "message": f"Error opening form: {str(e)}"}


@app.post("/fill_evaluation")
async def fill_evaluation(
        member_name: str = Form(...),
        score: int = Form(...),
        comments: str = Form(...)
):
    """Fill evaluation data for a team member"""
    try:
        if not evaluation_bot.current_form_open:
            return {"status": "error", "message": "No form is currently open. Please start evaluation first."}

        success = evaluation_bot.fill_evaluation_data(member_name, score, comments)

        if success:
            return {"status": "success", "message": f"Evaluation filled for {member_name}"}
        else:
            return {"status": "error",
                    "message": "Failed to fill evaluation data. The browser may have been closed or the form structure changed."}

    except Exception as e:
        logger.error(f"Error in fill_evaluation: {str(e)}")
        return {"status": "error", "message": f"Error filling evaluation: {str(e)}"}


@app.post("/submit")
async def submit_evaluation():
    """Submit the current form"""
    try:
        if not evaluation_bot.current_form_open:
            return {"status": "error", "message": "No form is currently open to submit."}

        success = evaluation_bot.submit_form()

        if success:
            return {"status": "success", "message": "Form submitted successfully"}
        else:
            return {"status": "error", "message": "Failed to submit form. Please check the browser window."}

    except Exception as e:
        logger.error(f"Error in submit: {str(e)}")
        return {"status": "error", "message": f"Error submitting form: {str(e)}"}


@app.post("/debug_form")
async def debug_form():
    """Debug the current form structure"""
    try:
        if not evaluation_bot.driver or not evaluation_bot._check_browser_status():
            return {"status": "error", "message": "No browser window is open. Please start an evaluation first."}

        # Get all radio button options
        debug_info = evaluation_bot.driver.execute_script("""
            var results = {};
            var listItems = document.querySelectorAll('[role="listitem"]');

            listItems.forEach(function(item, index) {
                var questionSpans = item.querySelectorAll('span');
                var questionText = '';
                var options = [];

                // Find question text
                for (var span of questionSpans) {
                    var text = span.textContent.trim();
                    if (text && !text.includes('*') && !text.includes('Your answer') && text.length > 2 && text.length < 100) {
                        if (!questionText || text.length > questionText.length) {
                            questionText = text;
                        }
                    }
                }

                // Find options for this question
                for (var span of questionSpans) {
                    var text = span.textContent.trim();
                    if (text && text !== questionText && !text.includes('*') && !text.includes('Your answer') && text.length < 50) {
                        if (!options.includes(text)) {
                            options.push(text);
                        }
                    }
                }

                if (questionText && options.length > 0) {
                    results[questionText] = options;
                }
            });

            return results;
        """)

        return {"status": "success", "form_structure": debug_info}

    except Exception as e:
        logger.error(f"Error in debug_form: {str(e)}")
        return {"status": "error", "message": f"Error analyzing form: {str(e)}"}


@app.get("/status")
async def get_status():
    """Get current system status"""
    try:
        browser_open = evaluation_bot.driver is not None and evaluation_bot._check_browser_status()
        form_open = evaluation_bot.current_form_open
        constants_set = bool(evaluation_bot.constants)

        return {
            "browser_open": browser_open,
            "form_open": form_open,
            "constants_set": constants_set,
            "constants": evaluation_bot.constants if constants_set else {}
        }
    except Exception as e:
        return {"error": str(e)}


@app.get("/debug", response_class=HTMLResponse)
async def debug_page(request: Request):
    """Debug page to show form structure"""
    return templates.TemplateResponse("debug.html", {"request": request})


@app.get("/reset")
async def reset():
    """Reset and go back to setup"""
    evaluation_bot.close()
    return RedirectResponse(url="/", status_code=303)


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)