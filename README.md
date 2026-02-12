# </> CampusCode

**CampusCode** is a comprehensive competitive programming and learning platform designed for educational institutes. It enables students to solve coding problems, participate in real-time contests, discuss solutions in forums, and track their progress via gamified leaderboards and detailed PDF reports.

---

## 🌟 Key Features

### 👨‍🎓 For Students
* **Code Execution Engine:** Integrated compiler supporting multiple languages (powered by Piston API).
* **Gamified Learning:** Earn XP, maintain daily streaks, and climb the Global and College Leaderboards.
* **Performance Analytics:** Download detailed PDF reports of your coding journey, including accuracy, difficulty distribution, and topic proficiency.
* **Community Forum:** Ask questions, reply to threads, and upvote the best answers to earn community XP.
* **Contests:** Register for and participate in scheduled coding contests with live timers.

### 🛡️ For Admins
* **Problem Management:** Create problems with specific constraints, difficulty levels, and hidden test cases.
* **Contest Management:** Schedule contests, set rules, and manage participants.
* **Dashboard:** View platform statistics including total users, problems, and active contests.

---

## 🛠️ Tech Stack

* **Backend:** Django (Python)
* **Database:** SQLite (Default) / PostgreSQL
* **Frontend:** HTML, CSS, JavaScript
* **PDF Generation:** ReportLab
* **API:** Piston API (for secure code execution)

---

## ⚙️ Local Installation & Setup

Follow these steps to run the project locally on your machine.

### 1. Clone the Repository
```bash
git clone [https://github.com/princekumar-git/campuscode.git](https://github.com/princekumar-git/campuscode.git)
cd campuscode

```

### 2. Set Up Virtual Environment

It is recommended to use a virtual environment to manage dependencies.

**Windows:**

```bash
python -m venv venv
venv\Scripts\activate

```

**macOS/Linux:**

```bash
python3 -m venv venv
source venv/bin/activate

```

### 3. Install Dependencies

Install the required Python packages.

```bash
pip install -r requirements.txt

```

*(Note: If `requirements.txt` is missing, install the core dependencies manually):*

```bash
pip install django requests reportlab

```

### 4. Database Setup

Initialize the database and apply migrations.

```bash
python manage.py makemigrations
python manage.py migrate

```

### 5. Create Admin User

To access the Admin Dashboard, create a superuser account.

```bash
python manage.py createsuperuser

```

### 6. Run the Server

Start the development server.

```bash
python manage.py runserver

```

Open your browser and navigate to: `http://127.0.0.1:8000/`

---

## 👥 Team Members

* **Prince Kumar** (Team Leader) - Database Architecture & Backend
* **Rupam Bhardwaj** - Backend Logic & Frontend Integration
* **Prashant Kumar** - Frontend Design & UI/UX

---
