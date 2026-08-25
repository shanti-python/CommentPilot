import logging
import re
from typing import Dict, Any, List, Optional
import httpx
from loguru import logger
from app.core.config import settings

class MetaAPIError(Exception):
    def __init__(self, message: str, status_code: int = 500, error_code: Optional[int] = None, error_subcode: Optional[int] = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.error_subcode = error_subcode

class MetaRateLimitError(MetaAPIError):
    pass

class MetaTokenExpiredError(MetaAPIError):
    pass

class MetaPermissionError(MetaAPIError):
    pass


class MetaClient:
    def __init__(self):
        self.base_url = "https://graph.facebook.com/v19.0"
        self.app_id = settings.META_APP_ID
        self.app_secret = settings.META_APP_SECRET

    async def _request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
        retries: int = 3
    ) -> Dict[str, Any]:
        """Perform HTTP requests to Meta Graph API with retry logic and error parsing."""
        # Check for mock token to bypass real network calls during testing/sandbox mode
        access_token = None
        if params and "access_token" in params:
            access_token = params["access_token"]
        elif json and "access_token" in json:
            access_token = json["access_token"]
            
        if access_token and (access_token == "mock_page_token" or str(access_token).startswith("mock")):
            logger.info(f"Bypassing Meta API call to {path} in Mock/Sandbox mode.")
            if "replies" in path:
                import time
                return {"id": f"mock_reply_{int(time.time())}"}
            elif "messages" in path or "message" in path:
                return {"message_id": "mock_message_ok"}
            elif "posts" in path:
                return {"data": []}
            return {"status": "success", "mock": True}

        url = f"{self.base_url}/{path.lstrip('/')}"
        
        # Build client
        async with httpx.AsyncClient(timeout=15.0) as client:
            for attempt in range(retries):
                try:
                    response = await client.request(method, url, params=params, json=json)
                    
                    # Parse error if status is not successful
                    if response.status_code != 200:
                        err_json = response.json()
                        error_details = err_json.get("error", {})
                        message = error_details.get("message", "Unknown Meta API error")
                        error_code = error_details.get("code")
                        error_subcode = error_details.get("error_subcode")
                        
                        # Detect permission restriction (Code 10 or 200-299)
                        is_permission_error = False
                        try:
                            code_val = int(error_code) if error_code is not None else None
                            if code_val == 10 or (code_val is not None and 200 <= code_val <= 299):
                                is_permission_error = True
                        except (ValueError, TypeError):
                            pass

                        if error_code == 10 or str(error_code) == "10":
                            logger.info(
                                f"Meta permission restriction on {method} {path} (Attempt {attempt+1}/{retries}). "
                                f"Code: {error_code}, Message: {message} (Will use local cache/mock data fallback)."
                            )
                        elif is_permission_error:
                            logger.warning(
                                f"Meta permission restriction on {method} {path} (Attempt {attempt+1}/{retries}). "
                                f"Code: {error_code}, Subcode: {error_subcode}, Message: {message}"
                            )
                        else:
                            logger.error(
                                f"Meta API error on {method} {path} (Attempt {attempt+1}/{retries}). "
                                f"Code: {error_code}, Subcode: {error_subcode}, Message: {message}"
                            )
                        
                        # Detect Token Expiration (Error code 190)
                        if error_code == 190:
                            raise MetaTokenExpiredError(message, response.status_code, error_code, error_subcode)
                            
                        # Detect Rate Limit (Error code 4, 17, 32, 613, or HTTP 429)
                        if response.status_code == 429 or error_code in [4, 17, 32, 613]:
                            raise MetaRateLimitError(message, response.status_code, error_code, error_subcode)
                            
                        # Detect Permission Restriction (Error code 10 or 200-299)
                        if is_permission_error:
                            raise MetaPermissionError(message, response.status_code, error_code, error_subcode)

                        # Other API Errors
                        raise MetaAPIError(message, response.status_code, error_code, error_subcode)
                        
                    return response.json()
                    
                except (httpx.RequestError, httpx.TimeoutException) as e:
                    logger.warning(f"Connection to Meta API failed (Attempt {attempt+1}/{retries}): {str(e)}")
                    if attempt == retries - 1:
                        raise MetaAPIError(f"Failed connecting to Meta Graph API: {str(e)}") from e
                    # Exponential backoff
                    import asyncio
                    await asyncio.sleep(2 ** attempt)

        raise MetaAPIError("Unknown error occurred during Meta API execution")

    async def get_long_lived_user_token(self, short_lived_token: str) -> str:
        """Exchange short-lived user token for a 60-day long-lived token."""
        logger.info("Exchanging short-lived user access token for a long-lived access token")
        params = {
            "grant_type": "fb_exchange_token",
            "client_id": self.app_id,
            "client_secret": self.app_secret,
            "fb_exchange_token": short_lived_token
        }
        res = await self._request("GET", "/oauth/access_token", params=params)
        return res.get("access_token", "")

    async def discover_accounts(self, long_lived_user_token: str) -> List[Dict[str, Any]]:
        """
        Discover Facebook Pages and connected Instagram Business Accounts.
        Returns a list of structured account info.
        """
        logger.info("Discovering Facebook Pages and connected Instagram Business Accounts")
        params = {
            "fields": "id,name,access_token,instagram_business_account{id,username,name,profile_picture_url}",
            "access_token": long_lived_user_token
        }
        
        res = await self._request("GET", "/me/accounts", params=params)
        pages_data = res.get("data", [])
        
        discovered_accounts = []
        for page in pages_data:
            insta_data = page.get("instagram_business_account")
            if insta_data:
                discovered_accounts.append({
                    "page_id": page["id"],
                    "page_name": page["name"],
                    "page_access_token": page["access_token"],
                    "instagram_business_account_id": insta_data["id"],
                    "instagram_username": insta_data.get("username", ""),
                    "instagram_name": insta_data.get("name", ""),
                    "instagram_profile_pic": insta_data.get("profile_picture_url", "")
                })
        
        logger.info(f"Discovered {len(discovered_accounts)} Instagram Business Accounts connected to pages")
        return discovered_accounts

    async def reply_to_comment(self, page_access_token: str, comment_id: str, message: str) -> str:
        """Reply publicly to an Instagram comment."""
        logger.info(f"Replying to Instagram comment {comment_id}")
        params = {
            "message": message,
            "access_token": page_access_token
        }
        res = await self._request("POST", f"/{comment_id}/replies", params=params)
        return res.get("id", "")

    async def send_dm_by_comment(self, page_access_token: str, comment_id: str, message_text: str) -> str:
        """
        Send a private Direct Message to a user who commented.
        Uses ManyChat's comment-to-DM entrypoint strategy.
        Private replies using comment_id are restricted to text-based messages by Meta's Graph API.
        This method automatically formats JSON templates into a clean, readable text message.
        """
        logger.info(f"Sending Direct Message to commenter of comment {comment_id}")
        params = {
            "access_token": page_access_token
        }

        # Auto-detect if message_text is a JSON template
        import json
        is_template = False
        payload_data = None
        try:
            stripped = message_text.strip()
            if stripped.startswith("{") and stripped.endswith("}"):
                payload_data = json.loads(stripped)
                is_template = True
        except Exception:
            pass

        if is_template and payload_data:
            dm_type = payload_data.get("dm_type", "message_template")
            if dm_type == "button_template":
                text_val = payload_data.get("text") or payload_data.get("title") or "Link below:"
                button_text = payload_data.get("button_text") or "Check Link"
                button_url = payload_data.get("button_url") or ""
                
                parts = [text_val]
                if button_url:
                    parts.append(f"{button_text}: {button_url}")
                
                message_payload = {
                    "text": "\n\n".join([p for p in parts if p])
                }
            elif dm_type == "image":
                text_val = payload_data.get("text") or payload_data.get("reply_text") or ""
                image_url = payload_data.get("image_url") or ""
                
                parts = []
                if text_val:
                    parts.append(text_val)
                if image_url:
                    parts.append(f"Image: {image_url}")
                
                message_payload = {
                    "text": "\n\n".join([p for p in parts if p])
                }
            else:
                # Text fallback
                message_payload = {
                    "text": payload_data.get("text") or payload_data.get("reply_text") or ""
                }
        else:
            message_payload = {
                "text": message_text
            }

        json_body = {
            "recipient": {
                "comment_id": comment_id
            },
            "message": message_payload
        }
        res = await self._request("POST", "/me/messages", params=params, json=json_body)
        return res.get("message_id", "")

    async def send_direct_dm(self, page_access_token: str, recipient_id: str, message_text: str) -> str:
        """
        Send a direct message to a user by their Instagram Scoped ID (IGSID).
        """
        logger.info(f"Sending direct DM to Instagram User {recipient_id}")
        params = {
            "access_token": page_access_token
        }

        # Auto-detect if message_text is a JSON template
        import json
        is_template = False
        payload_data = None
        try:
            stripped = message_text.strip()
            if stripped.startswith("{") and stripped.endswith("}"):
                payload_data = json.loads(stripped)
                is_template = True
        except Exception:
            pass

        if is_template and payload_data:
            dm_type = payload_data.get("dm_type", "message_template")
            if dm_type == "button_template":
                elements = [{
                    "title": payload_data.get("title") or payload_data.get("text") or "Info",
                    "subtitle": payload_data.get("subtitle") or "",
                    "buttons": [
                        {
                            "type": "web_url",
                            "url": payload_data.get("button_url") or "https://google.com",
                            "title": payload_data.get("button_text") or "View Link"
                        }
                    ]
                }]
                if payload_data.get("image_url"):
                    elements[0]["image_url"] = payload_data["image_url"]
                
                message_payload = {
                    "attachment": {
                        "type": "template",
                        "payload": {
                            "template_type": "generic",
                            "elements": elements
                        }
                    }
                }
            elif dm_type == "image":
                message_payload = {
                    "attachment": {
                        "type": "image",
                        "payload": {
                            "url": payload_data.get("image_url") or ""
                        }
                    }
                }
            else:
                # Text fallback
                message_payload = {
                    "text": payload_data.get("text") or payload_data.get("reply_text") or ""
                }
        else:
            message_payload = {
                "text": message_text
            }

        json_body = {
            "recipient": {
                "id": recipient_id
            },
            "message": message_payload
        }
        res = await self._request("POST", "/me/messages", params=params, json=json_body)
        return res.get("message_id", "")


        
    async def get_instagram_posts(self, instagram_business_account_id: str, page_access_token: str) -> List[Dict[str, Any]]:
        """Fetch list of media/posts on the Instagram business account."""
        logger.info(f"Fetching posts for Instagram Account {instagram_business_account_id}")
        params = {
            "fields": "id,caption,media_type,media_url,thumbnail_url,permalink,timestamp",
            "access_token": page_access_token
        }
        res = await self._request("GET", f"/{instagram_business_account_id}/media", params=params)
        return res.get("data", [])

    async def get_instagram_comments(self, media_id: str, page_access_token: str) -> List[Dict[str, Any]]:
        """Fetch comments for a specific Instagram post/media."""
        logger.info(f"Fetching comments for Instagram Media {media_id}")
        params = {
            "fields": "id,text,username,timestamp,parent_id,from",
            "access_token": page_access_token
        }
        if page_access_token == "mock_page_token" or str(page_access_token).startswith("mock"):
            return [
                {
                    "id": f"mock_comment_{media_id}_1",
                    "text": "This is a great mockup! Does it support real-time webhooks?",
                    "username": "tester_user",
                    "timestamp": "2026-08-03T15:00:00+0000",
                    "commenter_id": "mock_commenter_id_1"
                },
                {
                    "id": f"mock_comment_{media_id}_2",
                    "text": "Yes, it works perfectly!",
                    "username": "owner_user",
                    "timestamp": "2026-08-03T15:05:00+0000",
                    "parent_id": f"mock_comment_{media_id}_1",
                    "commenter_id": "mock_commenter_id_2"
                }
            ]
        try:
            res = await self._request("GET", f"/{media_id}/comments", params=params)
            comments_data = []
            for comment in res.get("data", []):
                from_data = comment.get("from", {})
                comments_data.append({
                    "id": comment["id"],
                    "text": comment.get("text", ""),
                    "username": comment.get("username") or from_data.get("username", "anonymous"),
                    "timestamp": comment.get("timestamp"),
                    "parent_id": comment.get("parent_id"),
                    "commenter_id": from_data.get("id")
                })
            return comments_data
        except MetaAPIError as e:
            logger.warning(f"Failed to fetch comments from Meta API: {e.message}")
            return []

    async def delete_comment(self, page_access_token: str, comment_id: str) -> bool:
        """Delete an Instagram comment or reply."""
        logger.info(f"Deleting Instagram comment/reply {comment_id}")
        params = {
            "access_token": page_access_token
        }
        if page_access_token == "mock_page_token" or str(page_access_token).startswith("mock"):
            return True
        res = await self._request("DELETE", f"/{comment_id}", params=params)
        return res.get("success", False)

    async def discover_facebook_pages(self, long_lived_user_token: str) -> List[Dict[str, Any]]:
        """Discover Facebook Pages for the user."""
        logger.info("Discovering Facebook Pages")
        params = {
            "fields": "id,name,access_token,picture{url}",
            "access_token": long_lived_user_token
        }
        if long_lived_user_token == "mock_user_token" or str(long_lived_user_token).startswith("mock"):
            return [
                {
                    "facebook_page_id": "mock_fb_page_1",
                    "name": "Mock Facebook Page",
                    "page_access_token": "mock_page_token",
                    "username": "mockfbpage",
                    "profile_picture_url": "https://placekitten.com/200/200"
                }
            ]
        res = await self._request("GET", "/me/accounts", params=params)
        pages_data = res.get("data", [])
        
        discovered_pages = []
        for page in pages_data:
            pic_url = page.get("picture", {}).get("data", {}).get("url", "") if page.get("picture") else ""
            discovered_pages.append({
                "facebook_page_id": page["id"],
                "name": page["name"],
                "page_access_token": page["access_token"],
                "username": page["name"].lower().replace(" ", ""),
                "profile_picture_url": pic_url
            })
        return discovered_pages

    async def get_facebook_posts(self, page_id: str, page_access_token: str) -> List[Dict[str, Any]]:
        """Fetch list of posts on the Facebook Page."""
        logger.info(f"Fetching posts for Facebook Page {page_id}")
        params = {
            "fields": "id,message,permalink_url,created_time,full_picture,attachments{media_type,type,url,media}",
            "access_token": page_access_token
        }
        if page_access_token == "mock_page_token" or str(page_access_token).startswith("mock"):
            return []
        try:
            res = await self._request("GET", f"/{page_id}/posts", params=params)
            posts_data = []
            for post in res.get("data", []):
                attachments = post.get("attachments", {}).get("data", [])
                media_type = "post"
                media_url = post.get("full_picture", "")
                permalink_url = post.get("permalink_url", "")
                
                if attachments:
                    first_att = attachments[0]
                    is_reel = "reel" in permalink_url.lower() or first_att.get("type") in ["video_inline", "video_autoplay", "video"]
                    if is_reel:
                        media_type = "reel"
                    
                    media_url = first_att.get("media", {}).get("image", {}).get("src", "") or first_att.get("url", "") or media_url

                posts_data.append({
                    "id": post["id"],
                    "caption": post.get("message", ""),
                    "media_type": media_type,
                    "media_url": media_url,
                    "thumbnail_url": media_url,
                    "permalink": permalink_url,
                    "timestamp": post.get("created_time")
                })
            
            # Fetch actual video reels from the page if they exist
            try:
                reels_params = {
                    "fields": "id,description,permalink_url,created_time,video",
                    "access_token": page_access_token
                }
                reels_res = await self._request("GET", f"/{page_id}/video_reels", params=reels_params)
                for reel in reels_res.get("data", []):
                    reel_id = reel["id"]
                    reel_permalink = reel.get("permalink_url", "")
                    is_duplicate = False
                    reel_digits = set(re.findall(r'\d{10,}', f"{reel_id} {reel_permalink}"))
                    for p in posts_data:
                        p_digits = set(re.findall(r'\d{10,}', f"{p['id']} {p.get('permalink', '')}"))
                        if p_digits.intersection(reel_digits):
                            is_duplicate = True
                            break
                    if not is_duplicate:
                        video_info = reel.get("video", {})
                        media_url = video_info.get("source", "") or video_info.get("picture", "")
                        posts_data.append({
                            "id": reel["id"],
                            "caption": reel.get("description", ""),
                            "media_type": "reel",
                            "media_url": media_url,
                            "thumbnail_url": video_info.get("picture", "") or media_url,
                            "permalink": reel_permalink,
                            "timestamp": reel.get("created_time")
                        })
            except Exception as e_reels:
                logger.info(f"Could not fetch live reels for Page {page_id}: {str(e_reels)}")
            
            return posts_data
        except MetaAPIError as e:
            logger.warning(f"Meta API error on GET /{page_id}/posts: {e.message}")
            return []

    async def get_facebook_comments(self, post_id: str, page_access_token: str) -> List[Dict[str, Any]]:
        """Fetch comments for a specific Facebook post."""
        logger.info(f"Fetching comments for Facebook Post {post_id}")
        params = {
            "fields": "id,message,from,created_time,parent",
            "access_token": page_access_token
        }
        try:
            res = await self._request("GET", f"/{post_id}/comments", params=params)
            comments_data = []
            for comment in res.get("data", []):
                from_data = comment.get("from", {})
                comments_data.append({
                    "id": comment["id"],
                    "text": comment.get("message", ""),
                    "username": from_data.get("name", from_data.get("username", "anonymous")),
                    "timestamp": comment.get("created_time"),
                    "parent_id": comment.get("parent", {}).get("id") if comment.get("parent") else None,
                    "commenter_id": from_data.get("id")
                })
            return comments_data
        except MetaAPIError as e:
            logger.warning(f"Failed to fetch Facebook comments from Meta API: {e.message}")
            return []


meta_client = MetaClient()
