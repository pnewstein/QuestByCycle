
# Integrating Instagram with Your Application

This guide provides detailed instructions on integrating Instagram with your application. It covers obtaining the Instagram Access Token, and Page ID, as well as assigning app roles to system users.

## Prerequisites

- A Facebook developer account.
- Access to Facebook Business Manager (if you are managing business assets).
- Administrative access to the Instagram account you are integrating.

## Step 1: Generate an Access Token

To interact with Instagram APIs, you need an access token. Follow these steps to generate one:

1. **Create a System User (if not already created)**:
   - Go to [Facebook Business Manager](https://business.facebook.com/).
   - Navigate to **Business Settings** > **Users** > **System Users**.
   - Click **Add** to create a new system user if one does not already exist.

2. **Assign App Role to System User**:
   - In **Business Settings**, go to **Users** > **System Users**.
   - Select the system user you want to assign a role to.
   - Click **Assign Assets**, select the app, and choose the appropriate role of **Tester**.

3. **Generate Access Token**:
   - In **System User Details**, click **Generate New Token**.
   - Select the app and choose the necessary permissions:
      - instagram_basic
      - instagram_content_publish
      - pages_manage_posts
      - pages_read_engagement
      - pages_read_user_content
      - publish_video
   - Click **Generate Token** and note down the **Access Token**.
s
## Step 4: Obtain Instagram Page ID

If your app needs to interact with a Instagram Page, you will need the Page ID:

1. **Go to [Facebook Business Manager](https://business.facebook.com/)**
   - Navigate to **Business Settings** > **Accounts** > **Instagram Accounts**.
   - Copy the **ID** that is shown under the Instagram page.