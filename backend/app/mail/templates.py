"""Email bodies. Copy in Italian, sentence case, informal — same voice as the app.

⚠️ Nothing about money goes in here. Not a balance, not a total, not a summary:
email is the least protected channel this system touches, and the only thing
worth putting in it is the link.
"""

SUBJECT = "Il tuo link di accesso"


def magic_link_text(link: str, minutes: int) -> str:
    return (
        "Ciao,\n\n"
        "ecco il link per entrare in Wallet:\n\n"
        f"{link}\n\n"
        f"Vale {minutes} minuti e si può usare una volta sola.\n"
        "Se non hai chiesto tu di accedere, ignora questa email.\n"
    )


def magic_link_html(link: str, minutes: int) -> str:
    # Deliberately plain: email clients mangle anything ambitious, and the
    # design system lives in the app, not in the inbox. The colours are the
    # tokens written out by hand, because an email cannot read a stylesheet.
    return f"""\
<!doctype html>
<html lang="it">
  <body style="margin:0;padding:24px;background:#060A08;
               font:400 15px/1.5 -apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
               color:#EDF5F0;">
    <div style="max-width:440px;margin:0 auto;background:#0E1613;border-radius:16px;
                border:1px solid rgba(126,255,192,.08);padding:28px;">
      <p style="margin:0 0 20px;font-weight:600;font-size:18px;">
        Wallet<span style="color:#3DF29B;">.</span>
      </p>
      <p style="margin:0 0 20px;">Ecco il link per entrare.</p>
      <p style="margin:0 0 24px;">
        <a href="{link}"
           style="display:inline-block;background:#3DF29B;color:#04130B;
                  text-decoration:none;font-weight:600;font-size:14px;
                  padding:13px 22px;border-radius:999px;">Entra</a>
      </p>
      <p style="margin:0;font-size:13px;color:#9FB4AA;">
        Vale {minutes} minuti e si pu&ograve; usare una volta sola.
        Se non hai chiesto tu di accedere, ignora questa email.
      </p>
    </div>
  </body>
</html>
"""
