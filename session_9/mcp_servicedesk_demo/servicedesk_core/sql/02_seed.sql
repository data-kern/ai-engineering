-- Sample data for the demo. Three employees and one service-desk agent (human).

INSERT INTO employees VALUES
    ('E-1001', 'Priya Nair',   'priya.nair@kernmart.example',   'employee'),
    ('E-1002', 'Rahul Mehta',  'rahul.mehta@kernmart.example',  'employee'),
    ('E-1003', 'Meera Iyer',   'meera.iyer@kernmart.example',   'employee'),
    ('S-9001', 'Anita Rao',    'anita.rao@kernmart.example',    'staff');

-- Priya forgot her password: locked after 5 failed attempts. The agent may unlock this.
-- Rahul is fine.
-- Meera is locked AND the security team put a hold on it (sign-ins from another country).
-- The agent must NOT unlock this one. It must escalate.
INSERT INTO accounts (employee_id, status, failed_attempts, security_hold, mfa_enrolled) VALUES
    ('E-1001', 'locked', 5, FALSE, TRUE),
    ('E-1002', 'active', 0, FALSE, TRUE),
    ('E-1003', 'locked', 7, TRUE,  TRUE);

INSERT INTO software_catalog (software, self_service, seats_total, approval_note) VALUES
    ('Zoom',               TRUE,  50, ''),
    ('Figma',              TRUE,   2, ''),
    ('Adobe Acrobat Pro',  TRUE,   2, ''),
    ('Tableau',            FALSE, 10, 'Needs approval from your manager and the data-governance team.'),
    ('Photoshop',          FALSE, 10, 'Needs approval from your manager.');

-- Two Acrobat seats already used, so the pool is empty: a good "I cannot do that" case.
INSERT INTO software_licenses (employee_id, software) VALUES
    ('E-1002', 'Adobe Acrobat Pro'),
    ('E-1003', 'Adobe Acrobat Pro');
-- One of two Figma seats used: the first request gets the last seat, the next one finds the pool empty.
INSERT INTO software_licenses (employee_id, software) VALUES
    ('E-1003', 'Figma');

INSERT INTO kb_articles (article_id, title, tags, body) VALUES
('KB-001', 'Connect to the company VPN',
 'vpn remote work connect disconnect drops',
 'Install the KernMart VPN client from the Software Centre. Sign in with your work email and approve the MFA prompt. If the VPN keeps disconnecting: (1) switch off any other VPN or proxy, (2) change the protocol from UDP to TCP in Settings > Connection, (3) restart the client. If it still drops after these three steps, open a ticket: the network team must look at your gateway logs.'),
('KB-002', 'Wi-Fi: connecting to KernMart-Corp',
 'wifi wi-fi wireless network office internet',
 'Choose the network KernMart-Corp (not KernMart-Guest). Sign in with your work email and password. If it keeps asking for a password, forget the network and join again. Laptops that were re-imaged need their device certificate renewed, which only the network team can do.'),
('KB-003', 'Forgot your password: self-service reset',
 'password reset forgot expired change login',
 'You can reset your own password: ask the service desk for a reset link. The link goes ONLY to the email address on file for your account and expires after 30 minutes. A password must be at least 14 characters and different from your last 5. We never read or set a password for you over chat.'),
('KB-004', 'My account is locked',
 'account locked lockout failed attempts sign in login unlock',
 'Accounts lock after 5 failed sign-in attempts. A locked account can be unlocked by the service desk, up to 3 times per day. Exception: if the security team has put a hold on the account (for example after sign-ins from another country) it must NOT be unlocked automatically. A human from the security team must review it. After an unlock, you may also need to reset your password: KB-003.'),
('KB-005', 'New phone: moving your MFA (authenticator)',
 'mfa 2fa authenticator new phone lost phone token codes',
 'Moving MFA to a new phone requires a human to verify your identity (video call or badge check). The service desk agent cannot do this. Open a ticket and escalate it to a human. If the OLD phone was lost or stolen, the urgency is high.'),
('KB-006', 'Printer shows offline',
 'printer print offline queue office',
 'Check the printer shows the green Ready light, then remove it from Settings > Printers and add it again by name (for example PRN-3F-EAST). Clear the print queue. If many people on the floor have the same problem the printer server is down: open a ticket for the infrastructure team.'),
('KB-007', 'Outlook is not syncing',
 'outlook email mail sync stuck inbox calendar',
 'Check you are online, then File > Account Settings > Repair. If the mailbox is still stuck, create a new Outlook profile (Control Panel > Mail > Show Profiles > Add). Mailbox size problems and shared mailbox access need the messaging team: open a ticket.'),
('KB-008', 'Laptop is slow',
 'laptop slow performance freezing hang restart disk',
 'Restart the laptop (a restart, not just closing the lid). Close browser tabs you do not use. Check that at least 15 GB of disk space is free. If the laptop is still slow after a restart and disk cleanup, it may be a hardware problem and needs a human technician.'),
('KB-009', 'Request software',
 'software install license licence app request catalog',
 'Some applications are self-service: a seat is assigned to you right away if one is free (Zoom, Figma, Adobe Acrobat Pro). Other applications need manager approval first (Tableau, Photoshop): this needs a human. If no seat is free, the request goes to the software asset team.'),
('KB-010', 'Suspicious email, phishing or a hacked account',
 'phishing suspicious email hacked compromised security malware virus clicked link',
 'If you clicked a link or entered your password on a page you do not trust, or you think your account is compromised: do not try to fix it yourself. This is a security incident. Escalate to a human immediately with urgency critical. The security team will lock the account and contact you.'),
('KB-011', 'Broken, lost or stolen laptop',
 'laptop broken screen lost stolen hardware replacement damaged',
 'Hardware replacement and lost or stolen devices need a human. For a lost or stolen laptop the urgency is critical (the device must be locked remotely). For a broken screen it is normal.');
