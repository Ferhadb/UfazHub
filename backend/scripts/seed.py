"""Seed the database with realistic UFAZ-flavoured fake data (development only).

    uv run python scripts/seed.py --reset   # wipe schema, migrate, seed

Grows with each slice. Writes demo logins to .playground/accounts.txt (gitignored).
"""

import argparse
import asyncio
import random
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import settings  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.db.session import SessionLocal, engine  # noqa: E402
from app.models.user import User  # noqa: E402
from app.models.library import ContentCourse  # noqa: E402
from app.schemas.content import ResourceIn  # noqa: E402
from app.schemas.library import CourseIn, PathIn, ProgramIn  # noqa: E402
from app.services import content as svc  # noqa: E402
from app.services import courses as course_svc  # noqa: E402

DEMO_PASSWORD = (
    "playground-pass"  # development fixture only; seeding refuses production
)

USERS = [
    ("admin@ufaz.az", "Leyla Hüseynova", "admin"),
    ("aygun@ufaz.az", "Aygün Məmmədova", "verified_ufazian"),
    ("rashad@ufaz.az", "Rəşad Əliyev", "verified_ufazian"),
    ("camille@ufaz.az", "Camille Durand", "verified_ufazian"),
    ("nigar@ufaz.az", "Nigar Qasımova", "user"),
    ("timur@ufaz.az", "Тимур Алиев", "user"),
]

# (slug, name, description) and (program, slug, name, level, tag whose items belong on the page)
PROGRAMS = [
    ("computer-science", "Computer Science", "Algorithms, systems and data."),
    ("engineering", "Engineering", "Process, petroleum and geological engineering."),
    ("mathematics", "Mathematics", "The shared mathematical core."),
]
COURSES = [
    ("computer-science", "algorithms-l2", "Algorithms", "L2", "algorithms"),
    ("computer-science", "databases-l2", "Databases", "L2", "databases"),
    ("computer-science", "programming-l1", "Programming", "L1", "programming"),
    ("mathematics", "algebra-l2", "Linear Algebra", "L2", "algebra"),
    ("engineering", "thermodynamics-l3", "Thermodynamics", "L3", "thermodynamics"),
]
PROFILES = {
    "aygun": ("Computer Science", 2026, "Teaching assistant, algebra"),
    "rashad": ("Computer Science", 2025, "Backend intern at a Baku fintech"),
    "camille": ("Engineering", 2027, "Exchange student from Strasbourg"),
}

# (author, title, description, type, category, difficulty, minutes, tags, link, research, extras)
R = [
    (
        "aygun",
        "Linear Algebra Done Right",
        "Axler's proof-first textbook. Pairs well with the L2 algebra course; skip the determinants chapter until the end, as the author does.",
        "book",
        "Mathematics",
        "intermediate",
        1800,
        ["algebra", "proofs", "L2"],
        "https://linear.axler.net/",
        False,
        dict(
            best_part="The chapter on eigenvalues without determinants.",
            warning="Exercises are hard. Do them anyway.",
            prerequisites="Basic set notation, a little patience.",
            student_note="Our group went through it one chapter a week during exam prep.",
        ),
    ),
    (
        "rashad",
        "CS50's Introduction to Computer Science",
        "Harvard's famous intro course, free. A gentle way into C, memory and algorithms before the L1 programming exam.",
        "course",
        "Computer science",
        "beginner",
        6000,
        ["programming", "C", "L1"],
        "https://cs50.harvard.edu/x/",
        False,
        dict(
            best_part="Week 4 on memory finally made pointers click.",
            student_note="Watch at 1.25x and do the problem sets.",
        ),
    ),
    (
        "camille",
        "Cours d'analyse réelle: polycopié complet",
        "Polycopié d'analyse L1 en français avec tous les exercices corrigés. Très utile avant les partiels.",
        "notes",
        "Mathematics",
        "beginner",
        480,
        ["analysis", "français", "L1", "past-exams"],
        "https://example.org/analyse-reelle.pdf",
        False,
        dict(student_note="Les corrigés sont fiables, relu par un enseignant."),
    ),
    (
        "aygun",
        "Əlgəbr və həndəsə: imtahan sualları (2019-2024)",
        "Past exam questions with worked solutions in Azerbaijani, collected by students over five years.",
        "exam",
        "Mathematics",
        "intermediate",
        300,
        ["past-exams", "algebra", "azərbaycan"],
        "https://example.org/elgebr-imtahan",
        False,
        dict(warning="Questions repeat; the grading scheme changed in 2022."),
    ),
    (
        "rashad",
        "Introduction to Algorithms (CLRS) study guide",
        "A condensed set of notes for the algorithms course: sorting, graphs, dynamic programming, with complexity cheat sheets.",
        "notes",
        "Computer science",
        "intermediate",
        900,
        ["algorithms", "L2", "proofs"],
        "https://example.org/clrs-guide",
        False,
        dict(best_part="The dynamic programming flow chart on page 12."),
    ),
    (
        "camille",
        "Missing Semester of Your CS Education",
        "MIT's practical course on the shell, git, debuggers and editors: the things nobody teaches but everyone needs.",
        "course",
        "Computer science",
        "beginner",
        900,
        ["tools", "git", "programming"],
        "https://missing.csail.mit.edu/",
        False,
        dict(best_part="The data wrangling lecture."),
    ),
    (
        "nigar",
        "Kaggle: Intro to Machine Learning",
        "Short hands-on notebooks covering decision trees and validation. Good first contact with scikit-learn before the AI elective.",
        "course",
        "Data science",
        "beginner",
        240,
        ["machine-learning", "python", "AI"],
        "https://www.kaggle.com/learn/intro-to-machine-learning",
        False,
        dict(prerequisites="Python basics and pandas."),
    ),
    (
        "rashad",
        "The Elements of Statistical Learning",
        "The reference for statistical learning. Dense, but free as a PDF, and the figures alone are worth the download.",
        "book",
        "Data science",
        "advanced",
        4800,
        ["machine-learning", "statistics", "research"],
        "https://hastie.su.domains/ElemStatLearn/",
        True,
        dict(
            warning="Not an introduction. Start with ISLR if this is your first stats-learning book."
        ),
    ),
    (
        "aygun",
        "Fundamentals of Heat and Mass Transfer: lecture slides",
        "Slides and problem sheets for thermodynamics and transfer processes, annotated by a third-year chemical engineering student.",
        "notes",
        "Engineering",
        "intermediate",
        600,
        ["thermodynamics", "engineering", "L3"],
        "https://example.org/heat-transfer-slides",
        False,
        dict(
            student_note="The annotated slides explain the sign conventions the professor skips."
        ),
    ),
    (
        "camille",
        "A gentle introduction to SQL and relational databases",
        "Interactive exercises that take you from SELECT to window functions. We used it for the databases project.",
        "tool",
        "Computer science",
        "beginner",
        360,
        ["sql", "databases", "L2"],
        "https://sqlbolt.com/",
        False,
        dict(best_part="Instant feedback in the browser."),
    ),
    (
        "nigar",
        "Physics Olympiad problem collection",
        "Problems from national olympiads with full solutions, sorted by topic: mechanics, optics, electricity.",
        "exam",
        "Physics",
        "advanced",
        1200,
        ["physics", "past-exams"],
        "https://example.org/physics-olympiad",
        False,
        dict(warning="Some solutions skip steps. Compare with a second source."),
    ),
    (
        "rashad",
        "Attention Is All You Need",
        "The transformer paper. Read it with the annotated version linked in the notes; the architecture diagram is the whole story.",
        "paper",
        "Data science",
        "advanced",
        120,
        ["machine-learning", "research", "AI"],
        "https://arxiv.org/abs/1706.03762",
        True,
        dict(best_part="Section 3.2 is where it all comes together."),
    ),
    (
        "aygun",
        "Caspian Sea hydrodynamics: a student survey",
        "Survey of measurements and models of Caspian Sea level change, compiled for a research methods seminar.",
        "paper",
        "Engineering",
        "advanced",
        180,
        ["research", "environment", "azərbaycan"],
        "https://example.org/caspian-survey",
        True,
        dict(student_note="A good model of how to structure a literature review."),
    ),
    (
        "camille",
        "Écrire en LaTeX: guide pour rapports et mémoires",
        "Template and guide for typesetting UFAZ reports in LaTeX, with French and Azerbaijani hyphenation set up.",
        "tool",
        "Writing",
        "beginner",
        90,
        ["latex", "français", "writing"],
        "https://example.org/latex-ufaz",
        False,
        dict(best_part="The ready-made title page template."),
    ),
    (
        "nigar",
        "Probability and Statistics for L2: worked examples",
        "Every distribution in the course explained once, with solved examples from past midterms.",
        "notes",
        "Mathematics",
        "intermediate",
        420,
        ["statistics", "past-exams", "L2"],
        "https://example.org/proba-l2",
        False,
        dict(),
    ),
    (
        "rashad",
        "Operating Systems: Three Easy Pieces",
        "Free online textbook on virtualization, concurrency and persistence. Chapters are short and funny.",
        "book",
        "Computer science",
        "intermediate",
        2400,
        ["operating-systems", "programming", "L3"],
        "https://pages.cs.wisc.edu/~remzi/OSTEP/",
        False,
        dict(best_part="The concurrency section."),
    ),
    (
        "aygun",
        "Organic chemistry reaction map",
        "A one-page map of the reactions from the O-chem course, redrawn by hand each semester and corrected by students.",
        "notes",
        "Chemistry",
        "intermediate",
        120,
        ["chemistry", "past-exams"],
        "https://example.org/orgchem-map",
        False,
        dict(warning="Check the Grignard section: version 1 had a typo."),
    ),
]


async def seed() -> None:
    random.seed(7)
    pw = await hash_password(DEMO_PASSWORD)
    async with SessionLocal() as db:
        users: dict[str, User] = {}
        for email, name, role in USERS:
            u = User(
                email=email,
                display_name=name,
                password_hash=pw,
                role=role,
                email_verified_at=datetime.now(UTC),
            )
            db.add(u)
            users[email.split("@")[0]] = u
        await db.flush()
        items = []
        for (
            author,
            title,
            desc,
            rtype,
            cat,
            diff,
            mins,
            tags,
            url,
            research,
            extra,
        ) in R:
            data = ResourceIn(
                title=title,
                description=desc,
                resource_type=rtype,
                category=cat,
                difficulty=diff,
                time_commitment_minutes=mins,
                tags=tags,
                links=[{"url": url, "label": "Open"}],
                is_research=research,
                **extra,
            )
            status = (
                "pending_review"
                if author == "nigar" and "Olympiad" in title
                else "published"
            )
            items.append(await svc.create_resource(db, users[author], data, status))
        voters = [u for u in users.values() if u.role != "admin"]
        for item in items:
            if item.status != "published":
                continue
            for voter in random.sample(voters, k=random.randint(0, len(voters))):
                if voter.id != item.author_id:
                    await svc.cast_vote(
                        db, voter, item.id, random.choice([1, 1, 1, -1])
                    )
            for voter in random.sample(voters, k=random.randint(0, 3)):
                await svc.set_bookmark(db, voter, item.id, True)
        for key, (faculty, year, job) in PROFILES.items():
            u = users[key]
            u.faculty, u.graduation_year, u.job_title = faculty, year, job
            u.bio = "Writes things down so the next cohort does not have to."
        admin = users["admin"]
        for slug, name, desc in PROGRAMS:
            await course_svc.create_program(
                db, admin, ProgramIn(slug=slug, name=name, description=desc)
            )
        for program, slug, name, level, tag in COURSES:
            await course_svc.create_course(
                db,
                admin,
                CourseIn(program_slug=program, slug=slug, name=name, level=level),
            )
            match = [
                i
                for i in items
                if i.status == "published" and tag in {t.slug for t in i.tags}
            ]
            if match:
                await course_svc.set_path(
                    db, admin, slug, PathIn(item_ids=[i.id for i in match[:3]])
                )
                for i in match[3:]:
                    db.add(
                        ContentCourse(
                            item_id=i.id,
                            course_id=(await course_svc.get_course(db, slug)).id,
                        )
                    )
        await db.commit()
    await engine.dispose()

    out = Path(__file__).resolve().parent.parent / ".playground"
    out.mkdir(exist_ok=True)
    lines = ["Playground logins (password for all: " + DEMO_PASSWORD + ")"]
    lines += [f"  {role:17} {email}" for email, _, role in USERS]
    (out / "accounts.txt").write_text("\n".join(lines) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true", help="drop and rebuild schema")
    args = parser.parse_args()
    if settings.APP_ENV == "production":
        sys.exit("refusing to seed a production database")
    if args.reset:
        subprocess.run(
            [sys.executable, "-m", "alembic", "downgrade", "base"], check=True
        )
    subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], check=True)
    asyncio.run(seed())
    print(f"seeded {len(USERS)} users and {len(R)} resources")


if __name__ == "__main__":
    main()
