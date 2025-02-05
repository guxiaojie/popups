import hashlib
from fastapi import FastAPI, File, UploadFile, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os
from starlette.responses import JSONResponse
from supabase import create_client, Client

app = FastAPI()
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

videos = []

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
supabase_client: Client = create_client(url, key)


# @app.get("/register", response_class=HTMLResponse)
# async def register():
#     response = supabase_client.auth.sign_up(
#         {"email": "sage.gu@ihealthlabs.com", "password": "password"}
#     )
#
#     print("response", response)
#
# @app.get("/signin", response_class=HTMLResponse)
# async def signin():
#     response = supabase_client.auth.sign_in_with_password(
#         {"email": "sage.gu@ihealthlabs.com", "password": "password"}
#     )
#     print("response", response)


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(
        "mimic.html", {"request": request, "videos": videos})


@app.get("/iframe", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(
        "popup.html", {"request": request, "videos": videos})

@app.get("/popup2", response_class=HTMLResponse)
async def popup2(request: Request):
    return templates.TemplateResponse(
        "popup2.html", {"request": request, "videos": videos})

async def get_authenticated_user(request: Request):
    """
    Middleware to extract user authentication token from headers
    and validate it with Supabase.
    """
    token = request.headers.get("Authorization")
    if not token or not token.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Unauthorized")

    token = token.split("Bearer ")[1]
    user = supabase_client.auth.get_user(token)

    if not user or "error" in user:
        raise HTTPException(status_code=401, detail="Invalid token")

    return user["user"]  # Returns the authenticated user's info


def generate_device_id(request: Request):
    """
    Generate a unique device ID using IP address + User-Agent hashed.
    """
    user_agent = request.headers.get("User-Agent", "unknown")
    ip_address = request.client.host or "unknown"

    device_string = f"{ip_address}-{user_agent}"
    device_id = hashlib.sha256(device_string.encode()).hexdigest()

    return device_id


# sage.gu@ihealthlabs.com
@app.post("/save-email")
async def save_email(request: Request):
    data = await request.json()
    email = data.get("email")
    device = data.get("device")

    print("request data", data)

    if not email or not device:
        return JSONResponse({"error": "Missing data"}, status_code=400)

    try:
        device_id = generate_device_id(request)  # Generate unique device ID
        print("device_id", device_id)

        response = supabase_client.table("users").insert({
            "email": email,
            "device_info": device_id,
            # "user_id": user["id"]  # Storing the authenticated user's ID
        }).execute()

        if "error" in response:
            return JSONResponse({"error": response["error"]["message"]}, status_code=500)

        return JSONResponse({"message": "Email saved successfully!"}, status_code=200)

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/save-phone")
async def save_phone(request: Request):
    data = await request.json()
    phone = data.get("phone")
    whatsapp = data.get("whatsapp")

    device_info = generate_device_id(request)  # Generate unique device ID
    print("device_id", device_info)

    if not phone or not whatsapp:
        return JSONResponse({"error": "Missing data"}, status_code=400)

    try:
        # Check if the device exists in the database
        existing_entry = supabase_client.table("users").select("*").eq("device_info", device_info).execute()

        if existing_entry.data:
            # Device exists → Update phone & WhatsApp
            response = supabase_client.table("users").update({
                "phone": phone,
                "whatsapp": whatsapp
            }).eq("device_info", device_info).execute()
        else:
            # Device does not exist → Insert new record
            response = supabase_client.table("users").insert({
                "device_info": device_info,
                "phone": phone,
                "whatsapp": whatsapp
            }).execute()

        if "error" in response:
            return JSONResponse({"error": response["error"]["message"]}, status_code=500)

        return JSONResponse({"message": "Phone details saved successfully!"}, status_code=200)

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
