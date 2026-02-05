// Supabase Configuration
// This file contains the Supabase credentials for the frontend
// In production, use environment variables or a backend proxy

window.SUPABASE_CONFIG = {
    url: 'YOUR_SUPABASE_URL',
    anonKey: 'YOUR_SUPABASE_ANON_KEY',

    // Initialize the Supabase client
    init: function () {
        if (this.url === 'YOUR_SUPABASE_URL' || this.anonKey === 'YOUR_SUPABASE_ANON_KEY') {
            console.warn('Supabase credentials not configured. Please update static/js/config.js');
            return null;
        }

        return supabase.createClient(this.url, this.anonKey);
    }
};
