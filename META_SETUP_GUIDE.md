# Meta API Setup & Multi-Account Connection Guide

This guide details the step-by-step procedures to configure your Meta Developer App, fix authentication errors, and connect multiple Instagram/Facebook accounts.

---

## 1. Resolving the "App not active" Error

### Why this happens
Your Meta Developer App is currently in **Development Mode**. By default, Meta restricts access in Development Mode to accounts explicitly associated with the app dashboard. If you try to log in with a new Facebook/Instagram account, Facebook blocks it with the **"App not active"** screen.

### How to resolve it
You have two options depending on your environment:

#### Option A: Add the new account as a Tester (Best for Development & Testing)
If you are testing new accounts locally, you do not need to verify the app. Instead, invite the new Facebook account as a Tester:
1. Log in to the [Meta for Developers Portal](https://developers.facebook.com/).
2. Select your App (**Test-app**).
3. In the left sidebar, navigate to **App Roles** -> **Roles**.
4. Click **Add Testers**.
5. Enter the Facebook Username, User ID, or email of the new account you want to connect, and click **Submit**.
6. On the new Facebook account, log in to Facebook, go to [Meta Developer Alerts/Invites](https://developers.facebook.com/requests/), and **Accept** the tester invitation.
7. You will now be able to log in without the "App not active" error.

#### Option B: Promote your App to Live Mode (Required for Production/Public Launch)
To allow any customer to connect their accounts without being added as a Tester:
1. Go to your App Dashboard settings.
2. Complete **Business Verification** under your Basic Settings.
3. Submit your app for **App Review** for the required permissions:
   * `instagram_basic`
   * `instagram_manage_comments`
   * `instagram_manage_messages`
   * `pages_show_list`
   * `pages_read_engagement`
4. Once approved, toggle the App status switch from **In Development** to **Live** at the top of the dashboard.

---

## 2. Enabling "Login with JavaScript SDK" for Ngrok

### Why this is required
Facebook blocks authentication requests initiated via JavaScript code (`FB.login`) unless the developer app explicitly authorizes the JavaScript SDK and lists your ngrok host domain as a trusted origin.

### How to configure it
1. Open your App Dashboard in [Meta for Developers](https://developers.facebook.com/).
2. In the left sidebar, navigate to **Use Cases** -> **Authentication and Account Creation** -> **Customize**.
3. Under the **Facebook Login** section, click **Go to Settings**.
4. Locate the toggle labeled **"Log in with JavaScript SDK"** and switch it to **Yes**.
5. In the input box labeled **"Allowed Domains for JavaScript SDK"**, add your secure ngrok address:
   ```text
   https://cyclonic-sam-difficultly.ngrok-free.dev
   ```
6. Click **Save Changes** at the bottom of the screen.

---

## 3. Step-by-Step Multi-Account Connection Workflow

Because Facebook's JavaScript SDK binds to your active browser cookies, follow this exact workflow to link a **new/different** account:

```
[Start App]
    │
    ▼
[Want to switch accounts?] ──Yes──► [Click 'Log Out of Facebook Browser Session']
    │                                                    │
    No                                                   ▼
    │                                     [Active Facebook cookies cleared]
    ▼                                                    │
[Click 'Link Active Session' to                          ▼
 connect current profile]                 [Click 'Link Active Session']
                                                         │
                                                         ▼
                                          [Empty Facebook Login prompt appears]
                                                         │
                                                         ▼
                                          [Enter credentials of new account]
```

### The Connection Steps:
1. Open the **Connect Meta Account** modal.
2. Click **🔴 Log Out of Facebook Browser Session** first. This logs you out of the active profile (e.g. *Anil Verma*) in your browser.
3. Click **⚡ Link Active Session** again.
4. An empty Facebook login popup will appear. Enter the email/username and password of your **new** account.
5. Grant permissions to the pages/channels, and the new account will connect successfully!
