import { test, expect } from '@playwright/test';

const REDIRECT = 'http://example.com/cb';

test.describe('LoginPage', () => {
  test('renders dark theme with Plus Jakarta Sans', async ({ page }) => {
    await page.goto(`/login?redirect_uri=${encodeURIComponent(REDIRECT)}`);

    // Dark background (gray-950 = rgb(10, 11, 15))
    const bodyBg = await page.evaluate(() =>
      getComputedStyle(document.body).backgroundColor
    );
    expect(bodyBg).toBe('rgb(10, 11, 15)');

    // Plus Jakarta Sans loaded
    const fontFamily = await page.evaluate(() =>
      getComputedStyle(document.body).fontFamily
    );
    expect(fontFamily).toContain('Plus Jakarta Sans');

    // Card visible, "Sign in to continue"
    await expect(page.getByText('Sign in to continue')).toBeVisible();
  });

  test('Google sign-in button navigates to Supabase authorize URL', async ({ page }) => {
    await page.goto(`/login?redirect_uri=${encodeURIComponent(REDIRECT)}&state=xyz`);

    // Stub navigation: capture the URL but don't follow it
    await page.route('**/auth/v1/authorize**', (route) => {
      route.fulfill({ status: 200, body: 'stubbed' });
    });

    const navPromise = page.waitForRequest('**/auth/v1/authorize**');
    await page.getByRole('button', { name: /Continue with Google/i }).click();
    const req = await navPromise;

    const url = new URL(req.url());
    expect(url.origin).toBe('https://test.supabase.co');
    expect(url.searchParams.get('provider')).toBe('google');

    const redirectTo = new URL(url.searchParams.get('redirect_to')!);
    expect(redirectTo.pathname).toBe('/callback');
    expect(redirectTo.searchParams.get('redirect_uri')).toBe(REDIRECT);
    expect(redirectTo.searchParams.get('state')).toBe('xyz');
  });

  test('shows divider between email form and Google button', async ({ page }) => {
    await page.goto(`/login?redirect_uri=${encodeURIComponent(REDIRECT)}`);
    await expect(page.locator('.divider')).toBeVisible();
    await expect(page.locator('.divider')).toContainText('or');
  });
});

test.describe('SignupPage', () => {
  test('renders Sign up with Google button', async ({ page }) => {
    await page.goto(`/signup?redirect_uri=${encodeURIComponent(REDIRECT)}`);
    await expect(page.getByRole('button', { name: /Sign up with Google/i })).toBeVisible();
  });
});

test.describe('CallbackPage', () => {
  test('displays error from hash fragment', async ({ page }) => {
    await page.goto(
      `/callback?redirect_uri=${encodeURIComponent(REDIRECT)}#error=access_denied&error_description=User+denied+access`
    );
    await expect(page.getByText(/User denied access/)).toBeVisible();
    await expect(page.getByRole('link', { name: /Back to sign in/i })).toBeVisible();
  });

  test('rejects invalid redirect_uri', async ({ page }) => {
    await page.goto(
      `/callback?redirect_uri=${encodeURIComponent('https://evil.com')}#access_token=tok&refresh_token=ref&expires_in=3600`
    );
    await expect(page.getByText(/not allowed/i)).toBeVisible();
  });

  test('processes valid tokens and redirects to allowed URI', async ({ page }) => {
    // Stub the SSO cookie endpoint and the final redirect destination
    await page.route('**/api/session', (route) =>
      route.fulfill({ status: 200, body: '{"ok":true}' })
    );
    await page.route('http://example.com/cb*', (route) =>
      route.fulfill({ status: 200, contentType: 'text/html', body: '<html><body>landed</body></html>' })
    );

    await page.goto(
      `/callback?redirect_uri=${encodeURIComponent(REDIRECT)}&state=s1#access_token=tok&refresh_token=ref&expires_in=3600`
    );

    await page.waitForURL(/example\.com\/cb#/);
    expect(page.url()).toContain('access_token=tok');
    expect(page.url()).toContain('refresh_token=ref');
    expect(page.url()).toContain('state=s1');
  });
});
