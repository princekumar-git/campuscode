# 🎓 CampusCode

![CampusCode Banner](https://via.placeholder.com/1200x400?text=CampusCode+Platform)

**CampusCode** is a competitive programming platform tailored for universities. It features a fully functional **browser-based IDE** integrated with the **Piston API** for code execution, a robust contest system, and comprehensive student performance tracking.

Built with **Django** (Backend) and **Tailwind CSS** (Frontend).

---

## ✨ Key Features

### 👨‍💻 Student Features

* **Browser-based IDE:** Write, run, and submit code (Python, C++, Java, JavaScript) directly in the browser.
* **Real-time Execution:** Powered by the **Piston API** for secure, sandboxed code execution.
* **Problem Set:** Browsable library of coding challenges with difficulty tags and acceptance rates.
* **Contest Arena:** Participate in live, upcoming, and past contests with automated timers.
* **Dashboard:** Track global rank, college rank, XP, and daily streaks.
* **Dark Mode:** Fully supported system-wide dark theme.

### 🛡️ Admin Features

* **Problem Management:** Create problems with descriptions, constraints, examples, and hidden test cases.
* **Contest Creation:** Schedule contests, assign problems, and define rules/prizes.
* **Analytics:** View total users, problem statistics, and submission insights.

---

## 📂 Project Structure

This project follows a standard Django architecture with a centralized `templates` directory for the Tailwind frontend.

```text
campuscode/
├── manage.py                   # Django command-line utility
├── campuscode/                 # Project configuration
│   ├── __init__.py
│   ├── settings.py             # Global settings (apps, DB, static files)
│   ├── urls.py                 # Main URL routing
│   └── wsgi.py                 # WSGI entry point
├── core/                       # Main application logic
│   ├── admin.py                # Admin panel configuration
│   ├── apps.py
│   ├── models.py               # DB models: User, Problem, Contest, TestCase
│   ├── tests.py
│   ├── urls.py                 # App-specific URL mapping
│   └── views.py                # Views: auth, dashboard, piston proxy, contest logic
├── templates/                  # Frontend templates (Tailwind)
│   ├── contest.html            # List of all contests
│   ├── contest_overview.html   # Specific contest details & rules
│   ├── dashboard.html          # Student dashboard (stats, streaks)
│   ├── editor.html             # CodeMirror IDE + Piston AJAX logic
│   ├── index.html              # Landing page & login/signup
│   ├── problem_page.html       # Problem description & solving interface
│   ├── problems.html           # Filterable list of practice problems
│   └── profile.html            # User profile settings
└── README.md                   # Project documentation
```

---

## 🛠️ Tech Stack

| Component             | Technology                                     |
| --------------------- | ---------------------------------------------- |
| **Backend Framework** | Django 5.x (Python)                            |
| **Frontend Styling**  | Tailwind CSS (CDN)                             |
| **Code Execution**    | Piston API (Remote REST API)                   |
| **Editor Component**  | CodeMirror 5 (JavaScript)                      |
| **Database**          | SQLite (development) / PostgreSQL (production) |

---

## 🚀 Getting Started

### Prerequisites

* Python 3.10+
* `pip` installed
* Git installed

---

### Installation

Clone the repository and enter the directory:

```bash
git clone https://github.com/yourusername/campuscode.git
cd campuscode
```

Create and activate a virtual environment:

```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
pip install django requests
```

---

### Database Setup

Apply migrations to set up the database:

```bash
python manage.py makemigrations
python manage.py migrate
```

Create an admin account:

```bash
python manage.py createsuperuser
```

---

### Running the Server

Start the Django development server:

```bash
python manage.py runserver
```

Open your browser and visit:

```
http://127.0.0.1:8000/
```

---

## ⚙️ Configuration Notes

### 🔧 Piston API (Code Execution)

The `views.py` file includes a proxy endpoint for the Piston API to prevent CORS issues from the frontend.

* **Endpoint:** `https://emkc.org/api/v2/piston`
* No API key required for the public tier.

---

### 🎨 Static Files

Tailwind CSS and FontAwesome are currently loaded via CDN in templates.

For production environments, it is recommended to:

* Set up Tailwind using Node.js and PostCSS
* Use Django’s static files pipeline

---

## 🤝 Contributing

Contributions are welcome and appreciated.

Fork the repository
Create a feature branch (`git checkout -b feature/YourFeature`)
Commit your changes
Push to your branch
Open a Pull Request


---

## 🧠 Vision

CampusCode aims to give colleges their own private competitive programming ecosystem. It is designed to help students practice problem-solving, compete in structured contests, and allow faculty to track performance and growth in a transparent and motivating way.

---

**Built for students. Designed for growth.** 🚀
