<?php
/**
 * Plugin Name: CZ Playlists
 * Status:      Discarded prototype — do not install.
 * Description: Registers the `playlist` custom post type, `host` taxonomy, and
 *              custom fields used to publish Convergence Zone episode pages
 *              from the playlist cache (shows/convergence-zone/playlists/cache/).
 * Version:     0.1.0
 * Author:      Far Pointer Radio
 *
 * Kept as a plugin (not theme functions.php) so the data model survives theme
 * updates and switches. Pair with the "CZ Playlists Child" theme (see
 * ../../wp-theme/cz-playlists-child/) for the single-playlist template, and
 * with Secure Custom Fields (or ACF) for the admin editing UI defined in
 * acf-json/group_playlist.json.
 */

if (!defined('ABSPATH')) {
    exit;
}

/**
 * Custom post type: playlist
 *
 * One post per broadcast, corresponding 1:1 with a
 * shows/convergence-zone/playlists/cache/broadcasts/YYYY-MM-DD.json record.
 */
add_action('init', function () {
    register_post_type('playlist', [
        'label'        => 'Playlists',
        'labels'       => [
            'name'          => 'Playlists',
            'singular_name' => 'Playlist',
            'add_new_item'  => 'Add New Playlist',
            'edit_item'     => 'Edit Playlist',
            'view_item'     => 'View Playlist',
            'search_items'  => 'Search Playlists',
        ],
        'public'       => true,
        'show_in_rest' => true,
        'rest_base'    => 'playlist',
        'supports'     => ['title', 'editor', 'custom-fields', 'revisions'],
        'has_archive'  => 'playlists',
        'rewrite'      => ['slug' => 'playlists', 'with_front' => false],
        'menu_icon'    => 'dashicons-format-audio',
        'show_in_menu' => true,
        'hierarchical' => false,
    ]);

    /**
     * Taxonomy: host
     *
     * One term per person who hosts the show (Jim Causey, MichaelG, occasional
     * guests). Populated from Broadcast.participants[].name. This is presentation
     * only — it is NOT the source of truth for Spinitron login attribution; the
     * cache's dj_ids field intentionally is not surfaced here (see
     * playlists/schema-rationale.md on why dj_ids != host).
     */
    register_taxonomy('host', 'playlist', [
        'label'        => 'Hosts',
        'labels'       => [
            'name'          => 'Hosts',
            'singular_name' => 'Host',
        ],
        'public'       => true,
        'show_in_rest' => true,
        'hierarchical' => false,
        'rewrite'      => ['slug' => 'host'],
    ]);
});

/**
 * Scalar custom fields, exposed to REST so the publisher script can write them
 * directly and so they're eligible targets for the Block Bindings API in the
 * single-playlist template.
 *
 * These are mirrored (same meta keys) by the ACF/SCF field group in
 * acf-json/group_playlist.json, which additionally adds the `hosts` and
 * `tracklist` repeaters for the admin editing UI. Registering the scalars here
 * too means Block Bindings still work even on a site where SCF/ACF is
 * temporarily deactivated.
 */
add_action('init', function () {
    $base = [
        'show_in_rest'  => true,
        'single'        => true,
        'auth_callback' => function () {
            return current_user_can('edit_posts');
        },
    ];

    register_post_meta('playlist', 'cz_air_datetime', $base + ['type' => 'string']);
    register_post_meta('playlist', 'cz_episode_number', $base + ['type' => 'integer']);
    register_post_meta('playlist', 'cz_description', $base + ['type' => 'string']);
    register_post_meta('playlist', 'cz_description_status', $base + ['type' => 'string']);
    register_post_meta('playlist', 'cz_mixcloud_url', $base + ['type' => 'string']);
    register_post_meta('playlist', 'cz_spinitron_playlist_url', $base + ['type' => 'string']);
});

/**
 * Point SCF/ACF's local-JSON sync at this plugin's acf-json/ folder.
 *
 * SCF/ACF only auto-scans the active theme's acf-json/ directory by default.
 * Adding this plugin's folder means the field group definition round-trips
 * through git (reviewable, portable across environments) instead of living
 * only in the site database.
 */
add_filter('acf/settings/load_json', function ($paths) {
    $paths[] = __DIR__ . '/acf-json';
    return $paths;
});

add_filter('acf/settings/save_json', function ($path) {
    return __DIR__ . '/acf-json';
});
