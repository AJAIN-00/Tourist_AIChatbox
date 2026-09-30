import os
import secrets
import functools
import logging
from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from flask_wtf.csrf import CSRFProtect, CSRFError
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------
load_dotenv()

# Configure structured logging (no stack-traces to client)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# ---------------------------------------------------------------------------
# Security configuration
# ---------------------------------------------------------------------------
_secret = os.getenv("SECRET_KEY", "")
if not _secret or _secret == "your-super-secret-key-change-this":
    # Warn loudly — do NOT silently generate a random one in production because
    # it invalidates all sessions on every restart.  Use a proper env var.
    logger.warning(
        "SECRET_KEY is not set or is the default placeholder. "
        "Sessions will be invalidated on every restart. "
        "Set a strong, stable SECRET_KEY in .env before deploying."
    )
    _secret = secrets.token_hex(32)

app.secret_key = _secret

# Session cookie hardening
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.getenv("FLASK_ENV") == "production",  # True in prod
    WTF_CSRF_TIME_LIMIT=3600,          # CSRF tokens expire after 1 hour
    WTF_CSRF_SSL_STRICT=False,         # Allow non-HTTPS in dev
    MAX_CONTENT_LENGTH=8 * 1024 * 1024,  # 8 MB upload limit
)

# CSRF protection (all POST/PUT/DELETE/PATCH forms protected automatically)
csrf = CSRFProtect(app)

# Rate limiting — uses in-memory storage (fine for single-process dev/prod)
limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    default_limits=["200 per hour"],
    storage_uri="memory://",
)

# ---------------------------------------------------------------------------
# File Upload
# ---------------------------------------------------------------------------
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "static", "uploads")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
# Magic bytes for allowed image types
ALLOWED_MAGIC = {
    b"\xff\xd8\xff",          # JPEG
    b"\x89PNG",               # PNG
    b"GIF87a", b"GIF89a",    # GIF
    b"RIFF",                  # WebP (RIFF....WEBP)
}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


def allowed_file(filename: str) -> bool:
    """Check extension allowlist only — caller must also verify magic bytes."""
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    )


def verify_magic_bytes(file_storage) -> bool:
    """
    Read the first 12 bytes to confirm the file is actually an image.
    Resets the stream position so the file can still be saved.
    """
    header = file_storage.read(12)
    file_storage.seek(0)
    return any(header.startswith(magic) for magic in ALLOWED_MAGIC)


def save_uploaded_image(file) -> "str | None":
    """Save an uploaded image file and return its URL path, or None if invalid."""
    if not (file and file.filename and allowed_file(file.filename)):
        return None
    if not verify_magic_bytes(file):
        logger.warning("File upload rejected: magic bytes do not match extension.")
        return None
    ext = file.filename.rsplit(".", 1)[1].lower()
    unique_name = secrets.token_hex(16) + "." + ext
    save_path = os.path.join(app.config["UPLOAD_FOLDER"], unique_name)
    file.save(save_path)
    return url_for("static", filename=f"uploads/{unique_name}")


# ---------------------------------------------------------------------------
# Import models / services (after app config)
# ---------------------------------------------------------------------------
from models.database import (  # noqa: E402
    init_db, seed_data, get_all_places, get_place_by_id,
    save_chat, verify_admin, add_place, update_place, delete_place,
)
from services.gemini_service import chat_with_gemini, generate_itinerary_ai  # noqa: E402
from services.weather_service import get_weather_for_city  # noqa: E402
from services.translate_service import translate_text  # noqa: E402
from services.maps_service import get_map_embed_url, get_directions_url  # noqa: E402

# Auto-initialize and seed DB on boot (syncs admin credentials from .env)
init_db()
seed_data()

# ---------------------------------------------------------------------------
# Emergency contacts (static — no user input involved)
# ---------------------------------------------------------------------------
EMERGENCY_CONTACTS = {
    "chennai": {
        "police": "100 (Chennai City Police: 044-23452345)",
        "ambulance": "108",
        "fire_service": "101",
        "nearest_hospital": "Rajiv Gandhi Government General Hospital (044-25305000)"
    },
    "coimbatore": {
        "police": "100 (Coimbatore City Police: 0422-2300600)",
        "ambulance": "108",
        "fire_service": "101",
        "nearest_hospital": "Government Medical College and Hospital (0422-2301393)"
    },
    "kanyakumari": {
        "police": "100 (Kanyakumari District Police: 04652-220100)",
        "ambulance": "108",
        "fire_service": "101",
        "nearest_hospital": "Government Headquarters Hospital, Nagercoil (04652-226050)"
    },
}

# ---------------------------------------------------------------------------
# DB initialisation
# ---------------------------------------------------------------------------
with app.app_context():
    init_db()
    seed_data()

# ---------------------------------------------------------------------------
# Security headers — applied to every response
# ---------------------------------------------------------------------------
@app.after_request
def set_security_headers(response):
    # Prevent MIME-type sniffing
    response.headers["X-Content-Type-Options"] = "nosniff"
    # Clickjacking protection
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
        "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://fonts.googleapis.com; "
        "img-src 'self' data: https://openweathermap.org https://img.icons8.com; "
        "font-src 'self' https://cdn.jsdelivr.net https://fonts.gstatic.com; "
        "frame-src https://maps.google.com https://www.google.com; "
        "connect-src 'self'; "
        "object-src 'none'; "
        "base-uri 'self'; "
        "form-action 'self';"
    )
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = (
        "geolocation=(), camera=(), microphone=(self), payment=()"
    )
    # Remove server fingerprinting
    response.headers.pop("Server", None)
    # Authenticated / sensitive responses: no caching
    if request.endpoint and (
        request.endpoint.startswith("admin") or
        request.endpoint in ("chat", "translate", "weather_info", "itinerary_plan")
    ):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
    return response


# ---------------------------------------------------------------------------
# CSRF error handler
# ---------------------------------------------------------------------------
@app.errorhandler(CSRFError)
def handle_csrf_error(e):
    logger.warning("CSRF validation failed for %s %s", request.method, request.path)
    flash("Your session has expired or the form was submitted incorrectly. Please try again.", "danger")
    return redirect(request.referrer or url_for("home")), 400


# ---------------------------------------------------------------------------
# Generic error handlers (no stack traces to client)
# ---------------------------------------------------------------------------
@app.errorhandler(404)
def not_found(e):
    return render_template("error.html", code=404, message="Page not found."), 404


@app.errorhandler(413)
def too_large(e):
    return jsonify({"error": "Upload too large. Maximum file size is 8 MB."}), 413


@app.errorhandler(429)
def ratelimit_error(e):
    logger.warning("Rate limit exceeded: %s %s from %s", request.method, request.path, get_remote_address())
    if request.is_json or request.path.startswith("/api/") or request.path in ("/chat", "/translate"):
        return jsonify({"error": "Too many requests. Please slow down."}), 429
    flash("Too many requests. Please wait a moment and try again.", "warning")
    return redirect(url_for("home")), 429


@app.errorhandler(500)
def internal_error(e):
    logger.exception("Internal server error")
    return render_template("error.html", code=500, message="Something went wrong. Please try again later."), 500


# ---------------------------------------------------------------------------
# Auth decorator
# ---------------------------------------------------------------------------
def login_required(f):
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("logged_in"):
            logger.info(
                "Unauthorised access attempt to %s from %s",
                request.path, get_remote_address()
            )
            flash("Please log in to access this page.", "warning")
            return redirect(url_for("admin_login"))
        return f(*args, **kwargs)
    return decorated_function


# ===========================================================================
# PAGE ROUTES
# ===========================================================================

@app.route("/")
def home():
    return render_template("index.html")


@app.route("/places")
def view_places():
    city_filter = request.args.get("city", "").strip()[:50]   # length cap
    search_query = request.args.get("search", "").strip()[:100].lower()

    places = get_all_places(city_filter if city_filter else None)

    if search_query:
        places = [
            p for p in places
            if search_query in p["name"].lower() or search_query in p["description"].lower()
        ]

    return render_template(
        "places.html",
        places=places,
        selected_city=city_filter,
        search_query=search_query,
    )


@app.route("/place/<int:place_id>")
def place_detail(place_id):
    place = get_place_by_id(place_id)
    if not place:
        flash("Tourist place not found.", "danger")
        return redirect(url_for("view_places"))

    map_url = get_map_embed_url(place["latitude"], place["longitude"], place["name"])
    directions_url = get_directions_url(place["latitude"], place["longitude"])

    return render_template(
        "place_detail.html",
        place=place,
        map_url=map_url,
        directions_url=directions_url,
    )


@app.route("/chatbot")
def view_chatbot():
    return render_template("chatbot.html")


@app.route("/itinerary")
def view_itinerary():
    return render_template("itinerary.html")


@app.route("/weather")
def view_weather():
    return render_template("weather.html")


# ===========================================================================
# API ENDPOINTS
# ===========================================================================

@app.route("/api/places")
@limiter.limit("60 per minute")
def api_places():
    city = request.args.get("city", "").strip()[:50]
    places = get_all_places(city if city else None)
    return jsonify(places)


@app.route("/api/place/<int:place_id>")
@limiter.limit("60 per minute")
def api_place(place_id):
    place = get_place_by_id(place_id)
    if not place:
        return jsonify({"error": "Place not found"}), 404
    return jsonify(place)


@app.route("/chat", methods=["POST"])
@csrf.exempt   # AJAX endpoint — protected by SameSite=Lax cookie + Content-Type check
@limiter.limit("20 per minute")
def chat():
    # Enforce JSON Content-Type to mitigate CSRF from form-based cross-origin requests
    if not request.is_json:
        return jsonify({"error": "Content-Type must be application/json"}), 415

    data = request.get_json(silent=True) or {}
    message = str(data.get("message", "")).strip()
    language = str(data.get("language", "en")).strip().lower()

    # Input validation
    if not message:
        return jsonify({"error": "Message content is required"}), 400
    if len(message) > 2000:
        return jsonify({"error": "Message too long (max 2000 characters)"}), 400

    ALLOWED_LANGUAGES = {"en", "ta", "hi", "te"}
    if language not in ALLOWED_LANGUAGES:
        language = "en"

    bot_response = chat_with_gemini(message)

    translated_response = bot_response
    if language != "en":
        translated_response = translate_text(bot_response, language)

    # Use a real session ID (generate one if absent)
    if "session_id" not in session:
        session["session_id"] = secrets.token_hex(16)
    session_id = session["session_id"]

    save_chat(session_id, message, translated_response, language)

    return jsonify({
        "original_response": bot_response,
        "response": translated_response,
    })


@app.route("/translate", methods=["POST"])
@csrf.exempt   # AJAX JSON endpoint
@limiter.limit("30 per minute")
def translate():
    if not request.is_json:
        return jsonify({"error": "Content-Type must be application/json"}), 415

    data = request.get_json(silent=True) or {}
    text = str(data.get("text", "")).strip()
    target_lang = str(data.get("target_language", "")).strip().lower()

    if not text or not target_lang:
        return jsonify({"error": "text and target_language are required"}), 400
    if len(text) > 5000:
        return jsonify({"error": "Text too long (max 5000 characters)"}), 400

    ALLOWED_LANGUAGES = {"ta", "hi", "te"}
    if target_lang not in ALLOWED_LANGUAGES:
        return jsonify({"error": "Unsupported target language"}), 400

    translated = translate_text(text, target_lang)
    return jsonify({"translated_text": translated})


@app.route("/weather/<city>")
@limiter.limit("30 per minute")
def weather_info(city):
    # Validate city against allowlist to prevent parameter injection
    ALLOWED_CITIES = {"chennai", "coimbatore", "kanyakumari"}
    city_key = city.lower().strip()
    if city_key not in ALLOWED_CITIES:
        return jsonify({"error": "City not supported. Choose from Chennai, Coimbatore, or Kanyakumari."}), 400
    weather_data = get_weather_for_city(city_key)
    if "error" in weather_data:
        return jsonify(weather_data), 400
    return jsonify(weather_data)


@app.route("/itinerary/<city>/<int:days>")
@limiter.limit("10 per minute")
def itinerary_plan(city, days):
    ALLOWED_CITIES = ["chennai", "coimbatore", "kanyakumari"]
    city_lower = city.lower().strip()
    if city_lower not in ALLOWED_CITIES:
        return jsonify({"error": "Itineraries are only supported for Chennai, Coimbatore, and Kanyakumari."}), 400
    if days not in [1, 2, 3]:
        return jsonify({"error": "Itinerary day count must be 1, 2, or 3 days."}), 400

    itinerary = generate_itinerary_ai(city.title(), days)
    return jsonify({"city": city.title(), "days": days, "itinerary": itinerary})


@app.route("/emergency/<city>")
@limiter.limit("30 per minute")
def emergency_info(city):
    city_key = city.lower().strip()
    contacts = EMERGENCY_CONTACTS.get(city_key)
    if not contacts:
        return jsonify({"error": "Emergency contacts only available for Chennai, Coimbatore, or Kanyakumari."}), 400
    return jsonify({"city": city.title(), "contacts": contacts})


# ===========================================================================
# ADMIN ROUTES
# ===========================================================================

@app.route("/admin/login", methods=["GET", "POST"])
@limiter.limit("10 per minute")   # brute-force protection on login
def admin_login():
    if session.get("logged_in"):
        return redirect(url_for("admin_dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if not username or not password:
            # Generic error — never reveal which field is wrong
            flash("Invalid credentials.", "danger")
            return render_template("admin_login.html")

        if verify_admin(username, password):
            session.clear()           # session fixation protection
            session["logged_in"] = True
            session["username"] = username
            logger.info("Admin login success for user '%s' from %s", username, get_remote_address())
            flash("Welcome to the Admin Panel!", "success")
            return redirect(url_for("admin_dashboard"))
        else:
            logger.warning(
                "Failed admin login attempt for user '%s' from %s",
                username, get_remote_address()
            )
            flash("Invalid credentials.", "danger")

    return render_template("admin_login.html")


@app.route("/admin/logout", methods=["POST"])
@login_required
def admin_logout():
    """Logout via POST to prevent CSRF-based forced logout."""
    logger.info("Admin '%s' logged out from %s", session.get("username"), get_remote_address())
    session.clear()
    flash("You have logged out successfully.", "info")
    return redirect(url_for("admin_login"))


@app.route("/admin")
@login_required
def admin_dashboard():
    places = get_all_places()
    return render_template("admin.html", places=places)


@app.route("/admin/place/new", methods=["GET", "POST"])
@login_required
def admin_new_place():
    if request.method == "POST":
        data = {
            "name": request.form.get("name", "").strip()[:200],
            "city": request.form.get("city", "").strip()[:100],
            "description": request.form.get("description", "").strip()[:5000],
            "history": request.form.get("history", "").strip()[:5000],
            "entry_fee": request.form.get("entry_fee", "").strip()[:100],
            "opening_time": request.form.get("opening_time", "").strip()[:50],
            "closing_time": request.form.get("closing_time", "").strip()[:50],
            "best_season": request.form.get("best_season", "").strip()[:100],
            "nearby_attractions": request.form.get("nearby_attractions", "").strip()[:500],
            "nearby_restaurants": request.form.get("nearby_restaurants", "").strip()[:500],
            "nearby_hotels": request.form.get("nearby_hotels", "").strip()[:500],
            "image_url": None,
        }

        # Validate city against allowlist
        ALLOWED_CITIES = {"Chennai", "Coimbatore", "Kanyakumari"}
        if data["city"] not in ALLOWED_CITIES:
            flash("Invalid city selection.", "danger")
            return render_template("admin_place_form.html", action="Add New", place=None)

        try:
            data["latitude"] = float(request.form.get("latitude") or 0.0)
            data["longitude"] = float(request.form.get("longitude") or 0.0)
        except ValueError:
            flash("Latitude and Longitude must be valid numbers.", "danger")
            return render_template("admin_place_form.html", action="Add New", place=None)

        # Handle image upload (magic-byte checked)
        image_file = request.files.get("image")
        uploaded_url = save_uploaded_image(image_file)
        if uploaded_url:
            data["image_url"] = uploaded_url
        elif request.form.get("image_url", "").strip():
            # Only allow http/https URLs — reject data: / javascript: / file: etc.
            raw_url = request.form.get("image_url", "").strip()[:500]
            if raw_url.startswith(("http://", "https://")):
                data["image_url"] = raw_url
            else:
                flash("Image URL must start with http:// or https://", "danger")
                return render_template("admin_place_form.html", action="Add New", place=None)

        if not data["name"] or not data["city"]:
            flash("Place name and City are required.", "danger")
            return render_template("admin_place_form.html", action="Add New", place=None)

        try:
            add_place(data)
            logger.info("Admin '%s' added new place: %s", session.get("username"), data["name"])
            flash("New tourist place added successfully!", "success")
            return redirect(url_for("admin_dashboard"))
        except Exception:
            logger.exception("Error adding place")
            flash("Error adding place. Please try again.", "danger")

    return render_template("admin_place_form.html", action="Add New", place=None)


@app.route("/admin/place/edit/<int:place_id>", methods=["GET", "POST"])
@login_required
def admin_edit_place(place_id):
    place = get_place_by_id(place_id)
    if not place:
        flash("Place not found.", "danger")
        return redirect(url_for("admin_dashboard"))

    if request.method == "POST":
        ALLOWED_CITIES = {"Chennai", "Coimbatore", "Kanyakumari"}
        data = {
            "name": request.form.get("name", "").strip()[:200],
            "city": request.form.get("city", "").strip()[:100],
            "description": request.form.get("description", "").strip()[:5000],
            "history": request.form.get("history", "").strip()[:5000],
            "entry_fee": request.form.get("entry_fee", "").strip()[:100],
            "opening_time": request.form.get("opening_time", "").strip()[:50],
            "closing_time": request.form.get("closing_time", "").strip()[:50],
            "best_season": request.form.get("best_season", "").strip()[:100],
            "nearby_attractions": request.form.get("nearby_attractions", "").strip()[:500],
            "nearby_restaurants": request.form.get("nearby_restaurants", "").strip()[:500],
            "nearby_hotels": request.form.get("nearby_hotels", "").strip()[:500],
            "image_url": None,
        }

        if data["city"] not in ALLOWED_CITIES:
            flash("Invalid city selection.", "danger")
            return render_template("admin_place_form.html", action="Edit", place=place)

        try:
            data["latitude"] = float(request.form.get("latitude") or 0.0)
            data["longitude"] = float(request.form.get("longitude") or 0.0)
        except ValueError:
            flash("Latitude and Longitude must be valid numbers.", "danger")
            return render_template("admin_place_form.html", action="Edit", place=place)

        image_file = request.files.get("image")
        uploaded_url = save_uploaded_image(image_file)
        if uploaded_url:
            data["image_url"] = uploaded_url
        elif request.form.get("image_url", "").strip():
            raw_url = request.form.get("image_url", "").strip()[:500]
            if raw_url.startswith(("http://", "https://")):
                data["image_url"] = raw_url
            else:
                flash("Image URL must start with http:// or https://", "danger")
                return render_template("admin_place_form.html", action="Edit", place=place)
        elif request.form.get("delete_image") == "1":
            data["image_url"] = ""

        if not data["name"] or not data["city"]:
            flash("Place name and City are required.", "danger")
            return render_template("admin_place_form.html", action="Edit", place=place)

        try:
            update_place(place_id, data)
            logger.info(
                "Admin '%s' updated place id=%s (%s)",
                session.get("username"), place_id, data["name"]
            )
            flash("Tourist place updated successfully!", "success")
            return redirect(url_for("admin_dashboard"))
        except Exception:
            logger.exception("Error updating place id=%s", place_id)
            flash("Error updating place. Please try again.", "danger")

    return render_template("admin_place_form.html", action="Edit", place=place)


@app.route("/admin/place/delete/<int:place_id>", methods=["POST"])
@login_required
def admin_delete_place(place_id):
    place = get_place_by_id(place_id)
    if not place:
        flash("Place not found.", "danger")
        return redirect(url_for("admin_dashboard"))

    try:
        delete_place(place_id)
        logger.info(
            "Admin '%s' deleted place id=%s ('%s')",
            session.get("username"), place_id, place["name"]
        )
        flash(f"'{place['name']}' has been deleted.", "success")
    except Exception:
        logger.exception("Error deleting place id=%s", place_id)
        flash("Error deleting place. Please try again.", "danger")

    return redirect(url_for("admin_dashboard"))


# ===========================================================================
# Start server (development only — gunicorn used in production)
# ===========================================================================
if __name__ == "__main__":
    debug_mode = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    host = "127.0.0.1"  # Never bind to 0.0.0.0 in development either
    port = int(os.getenv("PORT", "5000"))
    logger.info("Starting dev server on http://%s:%s (debug=%s)", host, port, debug_mode)
    app.run(debug=debug_mode, host=host, port=port)
