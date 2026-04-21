from pathlib import Path

p = Path("app/main.py")
s = p.read_text(encoding="utf-8")

old = '''    body = f"""Dear {greeting_name},

I hope you are doing well. I wanted to follow up on my application for the {job_title} position at {organization_name}, which I submitted on {application_date}.

I remain very interested in this opportunity and genuinely excited about the chance to contribute. The position stands out to me because of how closely it aligns with my background, my interests, and the kind of work I am hoping to grow in.

I would be grateful for any update you may be able to share regarding the status of my application. Thank you again for your time and consideration.

Best,
{st.secrets.get("user", {}).get("name", None) or __import__("os").environ.get("APP_USER_NAME", "Your Name")}
{st.secrets.get("user", {}).get("email", None) or __import__("os").environ.get("APP_USER_EMAIL", "your@email.com")}
"""'''

new = '''    import os
    user_secrets = st.secrets.get("user", {})
    user_name = user_secrets.get("name") or os.environ.get("APP_USER_NAME", "Your Name")
    job_type = (row.get("job_type") or "").lower()
    is_academic = any(k in job_type for k in ("academic", "research", "fellowship"))
    if is_academic:
        sender_email = user_secrets.get("university_email") or os.environ.get("APP_UNIVERSITY_EMAIL", user_secrets.get("email", "your@email.com"))
    else:
        sender_email = user_secrets.get("email") or os.environ.get("APP_USER_EMAIL", "your@email.com")

    body = f"""Dear {greeting_name},

I hope you are doing well. I wanted to follow up on my application for the {job_title} position at {organization_name}, which I submitted on {application_date}.

I remain very interested in this opportunity and genuinely excited about the chance to contribute. The position stands out to me because of how closely it aligns with my background, my interests, and the kind of work I am hoping to grow in.

I would be grateful for any update you may be able to share regarding the status of my application. Thank you again for your time and consideration.

Best,
{user_name}
{sender_email}
"""'''

s = s.replace(old, new)
p.write_text(s, encoding="utf-8")
print("Done")
