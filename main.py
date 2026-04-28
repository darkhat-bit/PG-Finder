from fastapi import FastAPI, Request, Form, Depends, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import psycopg
import pandas as pd
import numpy as np
from typing import Optional
from contextlib import asynccontextmanager
from database import get_db, create_tables, seed_data, PG, Review, User



# APP SETUP


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Runs when server starts - creates tables and adds sample data
    print("Starting PGFind...")
    create_tables()
    seed_data()
    print("Ready!")
    yield

app = FastAPI(title="PGFind", lifespan=lifespan)
templates = Jinja2Templates(directory="templates")

# HELPER FUNCTIONS


def get_current_user(request: Request, conn) -> Optional[User]:
    """Check cookie to see if user is logged in"""
    user_id = request.cookies.get("user_id")
    if not user_id:
        return None
    cur = conn.cursor()
    cur.execute("SELECT id, name, email, password, role FROM app_users WHERE id = %s;", (int(user_id),))
    row = cur.fetchone()
    cur.close()
    if row:
        return User(id=row[0], name=row[1], email=row[2], password=row[3], role=row[4])
    return None


def get_pg_by_id(conn, pg_id: int) -> Optional[PG]:
    """Get one PG and all its reviews by ID"""
    cur = conn.cursor()
    cur.execute("SELECT id, name, area, rent, contact, amenities, verified, gender, created_at, owner_id FROM app_pgs WHERE id = %s;", (pg_id,))
    row = cur.fetchone()
    if not row:
        cur.close()
        return None

    pg = PG(id=row[0], name=row[1], area=row[2], rent=row[3], contact=row[4],
            amenities=row[5], verified=row[6], gender=row[7], created_at=row[8], owner_id=row[9])

    cur.execute("SELECT id, pg_id, reviewer_name, rating, comment, created_at FROM app_reviews WHERE pg_id = %s ORDER BY created_at DESC;", (pg_id,))
    for r in cur.fetchall():
        pg.reviews.append(Review(id=r[0], pg_id=r[1], reviewer_name=r[2], rating=r[3], comment=r[4], created_at=r[5]))

    cur.close()
    return pg


def get_all_pgs(conn) -> list:
    """Get all PGs from database"""
    cur = conn.cursor()
    cur.execute("SELECT id, name, area, rent, contact, amenities, verified, gender, created_at, owner_id FROM app_pgs;")
    pgs = []
    for row in cur.fetchall():
        pgs.append(PG(id=row[0], name=row[1], area=row[2], rent=row[3], contact=row[4],
                      amenities=row[5], verified=row[6], gender=row[7], created_at=row[8], owner_id=row[9]))
    cur.close()
    return pgs


def get_reviews_for_pg(conn, pg_id: int) -> list:
    """Get all reviews for a specific PG"""
    cur = conn.cursor()
    cur.execute("SELECT id, pg_id, reviewer_name, rating, comment, created_at FROM app_reviews WHERE pg_id = %s ORDER BY created_at DESC;", (pg_id,))
    reviews = []
    for r in cur.fetchall():
        reviews.append(Review(id=r[0], pg_id=r[1], reviewer_name=r[2], rating=r[3], comment=r[4], created_at=r[5]))
    cur.close()
    return reviews


def get_all_reviews(conn) -> list:
    """Get every review in the database"""
    cur = conn.cursor()
    cur.execute("SELECT id, pg_id, reviewer_name, rating, comment, created_at FROM app_reviews;")
    reviews = []
    for r in cur.fetchall():
        reviews.append(Review(id=r[0], pg_id=r[1], reviewer_name=r[2], rating=r[3], comment=r[4], created_at=r[5]))
    cur.close()
    return reviews


def get_unique_areas(conn) -> list:
    """Get list of unique areas for the dropdown"""
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT area FROM app_pgs ORDER BY area;")
    areas = [row[0] for row in cur.fetchall()]
    cur.close()
    return areas


# ROUTE 1: Homepage

@app.get("/", response_class=HTMLResponse)
def homepage(request: Request, conn: psycopg.Connection = Depends(get_db)):
    current_user = get_current_user(request, conn)

    # Count total PGs
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM app_pgs;")
    total_pgs = cur.fetchone()[0]
    cur.close()

    areas = get_unique_areas(conn)

    # Get only verified PGs for the featured section
    all_pgs = get_all_pgs(conn)
    featured_pgs = [pg for pg in all_pgs if pg.verified][:4]

    # Calculate average rating for each featured PG
    for pg in featured_pgs:
        reviews = get_reviews_for_pg(conn, pg.id)
        if reviews:
            ratings = [r.rating for r in reviews]
            pg.avg_rating = round(sum(ratings) / len(ratings), 1)
        else:
            pg.avg_rating = 0

    return templates.TemplateResponse("index.html", {
        "request": request,
        "total_pgs": total_pgs,
        "areas": areas,
        "featured_pgs": featured_pgs,
        "current_user": current_user
    })

# ROUTE 2: Login / Register / Logout

@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "current_user": None, "error": None})


@app.post("/login")
def login(email: str = Form(...), password: str = Form(...), conn: psycopg.Connection = Depends(get_db)):
    cur = conn.cursor()
    cur.execute("SELECT id, name, email, password, role FROM app_users WHERE email = %s AND password = %s;", (email, password))
    row = cur.fetchone()
    cur.close()

    if row:
        user = User(id=row[0], name=row[1], email=row[2], password=row[3], role=row[4])
        redirect = RedirectResponse(url="/", status_code=303)
        redirect.set_cookie(key="user_id", value=str(user.id))
        return redirect

    return templates.TemplateResponse("login.html", {"request": {}, "error": "Wrong email or password!", "current_user": None})


@app.get("/register", response_class=HTMLResponse)
def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request, "current_user": None, "error": None})


@app.post("/register")
def register(name: str = Form(...), email: str = Form(...), password: str = Form(...), role: str = Form(...), conn: psycopg.Connection = Depends(get_db)):
    # Check if email already used
    cur = conn.cursor()
    cur.execute("SELECT id FROM app_users WHERE email = %s;", (email,))
    if cur.fetchone():
        cur.close()
        return templates.TemplateResponse("register.html", {"request": {}, "error": "Email already registered!", "current_user": None})

    # Add new user
    try:
        cur.execute("INSERT INTO app_users (name, email, password, role) VALUES (%s, %s, %s, %s) RETURNING id;", (name, email, password, role))
        new_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        redirect = RedirectResponse(url="/", status_code=303)
        redirect.set_cookie(key="user_id", value=str(new_id))
        return redirect
    except Exception as e:
        conn.rollback()
        cur.close()
        print(f"Register error: {e}")
        return templates.TemplateResponse("register.html", {"request": {}, "error": "Something went wrong!", "current_user": None})


@app.get("/logout")
def logout():
    redirect = RedirectResponse(url="/", status_code=303)
    redirect.delete_cookie("user_id")
    return redirect


# ROUTE 3: Search PGs
# Uses Pandas for filtering

@app.get("/search", response_class=HTMLResponse)
def search_pgs(
    request: Request,
    area: str = Query(default=""),
    max_rent: int = Query(default=50000),
    gender: str = Query(default=""),
    conn: psycopg.Connection = Depends(get_db)
):
    all_pgs = get_all_pgs(conn)

    # Build a list of dicts so we can put it in a Pandas DataFrame
    pg_data = []
    for pg in all_pgs:
        reviews = get_reviews_for_pg(conn, pg.id)
        ratings = [r.rating for r in reviews]
        pg_data.append({
            "id": pg.id,
            "name": pg.name,
            "area": pg.area,
            "rent": pg.rent,
            "contact": pg.contact,
            "amenities": pg.amenities,
            "verified": pg.verified,
            "gender": pg.gender,
            "avg_rating": round(float(np.mean(ratings)), 1) if ratings else 0,
            "review_count": len(ratings)
        })

    df = pd.DataFrame(pg_data)

    # Filter using Pandas
    if area:
        df = df[df["area"].str.contains(area, case=False, na=False)]
    if max_rent < 50000:
        df = df[df["rent"] <= max_rent]
    if gender:
        df = df[(df["gender"] == gender) | (df["gender"] == "Any")]

    results = df.to_dict("records") if not df.empty else []
    areas = get_unique_areas(conn)

    return templates.TemplateResponse("search.html", {
        "request": request,
        "pgs": results,
        "total_results": len(results),
        "areas": areas,
        "selected_area": area,
        "max_rent": max_rent if max_rent < 50000 else "",
        "selected_gender": gender,
        "current_user": get_current_user(request, conn)
    })


# ROUTE 4: PG Detail Page
@app.get("/pg/{pg_id}", response_class=HTMLResponse)
def pg_details(request: Request, pg_id: int, conn: psycopg.Connection = Depends(get_db)):
    pg = get_pg_by_id(conn, pg_id)
    if not pg:
        return templates.TemplateResponse("error.html", {"request": request, "message": "PG not found!", "current_user": None})

    reviews = get_reviews_for_pg(conn, pg_id)

    # NumPy for stats
    ratings = [r.rating for r in reviews]
    if ratings:
        avg_rating = round(float(np.mean(ratings)), 1)
        rating_std = round(float(np.std(ratings)), 1)
    else:
        avg_rating = 0
        rating_std = 0

    amenities_list = pg.amenities.split(", ") if pg.amenities else []

    return templates.TemplateResponse("pg_detail.html", {
        "request": request,
        "pg": pg,
        "reviews": reviews,
        "avg_rating": avg_rating,
        "rating_std": rating_std,
        "total_reviews": len(reviews),
        "amenities_list": amenities_list,
        "current_user": get_current_user(request, conn)
    })


# ROUTE 5: Submit a Review
@app.post("/pg/{pg_id}/review")
def add_review(pg_id: int, reviewer_name: str = Form(...), rating: int = Form(...), comment: str = Form(default=""), conn: psycopg.Connection = Depends(get_db)):
    try:
        cur = conn.cursor()
        cur.execute("INSERT INTO app_reviews (pg_id, reviewer_name, rating, comment) VALUES (%s, %s, %s, %s);", (pg_id, reviewer_name, rating, comment))
        conn.commit()
        cur.close()
    except Exception as e:
        conn.rollback()
        print(f"Review error: {e}")
    return RedirectResponse(url=f"/pg/{pg_id}", status_code=303)


# ROUTE 6: Add New PG (owner/admin only)
@app.get("/add-pg", response_class=HTMLResponse)
def add_pg_form(request: Request, conn: psycopg.Connection = Depends(get_db)):
    user = get_current_user(request, conn)
    if not user or user.role not in ["owner", "admin"]:
        return RedirectResponse(url="/login", status_code=303)
    return templates.TemplateResponse("add_pg.html", {"request": request, "current_user": user})


@app.post("/add-pg")
def add_pg(
    request: Request,
    name: str = Form(...),
    area: str = Form(...),
    rent: int = Form(...),
    contact: str = Form(default=""),
    amenities: str = Form(default=""),
    gender: str = Form(default="Any"),
    conn: psycopg.Connection = Depends(get_db)
):
    user = get_current_user(request, conn)
    owner_id = user.id if user else 0
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO app_pgs (name, area, rent, contact, amenities, gender, verified, owner_id) VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id;",
            (name, area, rent, contact, amenities, gender, False, owner_id)
        )
        new_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        return RedirectResponse(url=f"/pg/{new_id}", status_code=303)
    except Exception as e:
        conn.rollback()
        print(f"Add PG error: {e}")
        return RedirectResponse(url="/add-pg", status_code=303)


# ROUTE 7: Admin - Verify / Delete PG
@app.get("/admin/verify/{pg_id}")
def toggle_verify(pg_id: int, request: Request, conn: psycopg.Connection = Depends(get_db)):
    user = get_current_user(request, conn)
    if not user or user.role != "admin":
        return RedirectResponse(url="/", status_code=303)
    cur = conn.cursor()
    cur.execute("UPDATE app_pgs SET verified = NOT verified WHERE id = %s;", (pg_id,))
    conn.commit()
    cur.close()
    return RedirectResponse(url=f"/pg/{pg_id}", status_code=303)


@app.get("/admin/delete/{pg_id}")
def delete_pg(pg_id: int, request: Request, conn: psycopg.Connection = Depends(get_db)):
    user = get_current_user(request, conn)
    if not user or user.role != "admin":
        return RedirectResponse(url="/", status_code=303)
    cur = conn.cursor()
    cur.execute("DELETE FROM app_reviews WHERE pg_id = %s;", (pg_id,))
    cur.execute("DELETE FROM app_pgs WHERE id = %s;", (pg_id,))
    conn.commit()
    cur.close()
    return RedirectResponse(url="/search", status_code=303)


# ROUTE 8: Analytics (Pandas + NumPy)
@app.get("/analytics", response_class=HTMLResponse)
def analytics(request: Request, conn: psycopg.Connection = Depends(get_db)):
    all_pgs = get_all_pgs(conn)
    all_reviews = get_all_reviews(conn)

    # Make a Pandas DataFrame from PG data
    pg_data = [{"name": pg.name, "area": pg.area, "rent": pg.rent, "gender": pg.gender, "verified": pg.verified} for pg in all_pgs]
    df = pd.DataFrame(pg_data)

    # Pandas groupby for average rent by area
    rent_by_area = df.groupby("area")["rent"].mean().round(0).astype(int).to_dict()
    count_by_area = df.groupby("area")["name"].count().to_dict()
    gender_dist = df["gender"].value_counts().to_dict()
    verified_count = int(df[df["verified"] == True].shape[0])
    unverified_count = int(df[df["verified"] == False].shape[0])

    # NumPy for price stats
    rents = np.array(df["rent"].tolist())
    price_stats = {
        "mean":   int(np.mean(rents)),
        "median": int(np.median(rents)),
        "min":    int(np.min(rents)),
        "max":    int(np.max(rents)),
        "std":    int(np.std(rents)),
    }

    # NumPy for rating stats
    ratings = np.array([r.rating for r in all_reviews])
    if len(ratings) > 0:
        rating_stats = {
            "mean": round(float(np.mean(ratings)), 1),
            "median": float(np.median(ratings)),
            "total_reviews": len(ratings),
        }
        rating_distribution = {f"{i} Star": int(np.sum(ratings == i)) for i in range(1, 6)}
    else:
        rating_stats = {"mean": 0, "median": 0, "total_reviews": 0}
        rating_distribution = {}

    return templates.TemplateResponse("analytics.html", {
        "request": request,
        "rent_by_area": rent_by_area,
        "count_by_area": count_by_area,
        "gender_dist": gender_dist,
        "price_stats": price_stats,
        "rating_stats": rating_stats,
        "rating_distribution": rating_distribution,
        "verified_count": verified_count,
        "unverified_count": unverified_count,
        "total_pgs": len(all_pgs),
        "current_user": get_current_user(request, conn)
    })


# RUN THE APP
if __name__ == "__main__":
    import uvicorn
    print("Starting PGFind on http://localhost:8080")
    uvicorn.run(app, host="0.0.0.0", port=8080)