<?php
/**
 * Plugin Name: Travelmemo Content API
 * Description: REST API for blog content extraction and automation integration
 * Version: 1.0.1
 * Author: Walter Schärer
 * Author URI: https://travelmemo.com/author/walter-schaerer
 * Text Domain: travelmemo-content
 */

// Exit if accessed directly
if (!defined('ABSPATH')) {
    exit;
}

class Travelmemo_Content_API {

    /**
     * Constructor - register hooks
     */
    public function __construct() {
        // Register REST API routes
        add_action('rest_api_init', array($this, 'register_routes'));

        // Add CORS headers for cross-origin requests
        add_action('rest_api_init', array($this, 'add_cors_headers'));
    }

    /**
     * Register REST API routes
     */
    public function register_routes() {
        // Content extraction endpoint
        register_rest_route('travelmemo-content/v1', '/extract/(?P<slug>[a-zA-Z0-9-]+)', array(
            'methods' => 'GET',
            'callback' => array($this, 'extract_content'),
            'permission_callback' => '__return_true', // Public access for automation
            'args' => array(
                'slug' => array(
                    'required' => true,
                    'validate_callback' => function($param, $request, $key) {
                        return is_string($param) && !empty($param);
                    }
                ),
                'auth_key' => array(
                    'required' => false,
                    'validate_callback' => function($param, $request, $key) {
                        return is_string($param);
                    }
                )
            )
        ));

        // Posts listing endpoint (optional)
        register_rest_route('travelmemo-content/v1', '/posts', array(
            'methods' => 'GET',
            'callback' => array($this, 'list_posts'),
            'permission_callback' => '__return_true',
            'args' => array(
                'per_page' => array(
                    'default' => 10,
                    'validate_callback' => function($param, $request, $key) {
                        return is_numeric($param) && $param <= 100;
                    }
                )
            )
        ));
    }

    /**
     * Extract blog content for automation
     *
     * @param WP_REST_Request $request
     * @return WP_REST_Response|WP_Error
     */
    public function extract_content($request) {
        $slug = $request['slug'];
        $auth_key = $request->get_param('auth_key');

        // Optional simple authentication
        if ($auth_key && $auth_key !== 'tm-post-retrieval') {
            return new WP_Error('invalid_auth', 'Invalid authentication key', array('status' => 401));
        }

        // Find post by slug
        $post = get_page_by_path($slug, OBJECT, 'post');

        if (!$post) {
            return new WP_Error('not_found', 'Post not found', array('status' => 404));
        }

        // Check if post is published
        if ($post->post_status !== 'publish') {
            return new WP_Error('not_published', 'Post not published', array('status' => 404));
        }

        // Get full content (bypasses Elementor read-more)
        $content = apply_filters('the_content', $post->post_content);

        // Extract clean text content
        $text_content = wp_strip_all_tags($content);

        // Split into meaningful paragraphs
        $paragraphs = $this->extract_paragraphs($text_content);

        // Get additional metadata
        $featured_image = has_post_thumbnail($post->ID) ?
            get_the_post_thumbnail_url($post->ID, 'full') : '';

        $categories = wp_get_post_categories($post->ID, array('fields' => 'names'));
        $tags = wp_get_post_tags($post->ID, array('fields' => 'names'));

        // Extract headings from content
        $headings = $this->extract_headings($content);

        // Extract images from content
        $images = $this->extract_images($content);

        return rest_ensure_response(array(
            'success' => true,
            'data' => array(
                'id' => $post->ID,
                'title' => get_the_title($post),
                'slug' => $post->post_name,
                'url' => get_permalink($post),
                'excerpt' => get_the_excerpt($post),
                'content' => $content, // Full HTML content
                'text_content' => $text_content, // Plain text
                'paragraphs' => $paragraphs, // Clean paragraphs for automation
                'headings' => $headings, // Extracted headings
                'images' => $images, // Image references
                'featured_image' => $featured_image,
                'categories' => $categories,
                'tags' => $tags,
                'date' => $post->post_date,
                'modified' => $post->post_modified,
                'author' => get_the_author_meta('display_name', $post->post_author),
                'word_count' => str_word_count($text_content),
                'source' => 'travelmemo_content_api',
                'api_version' => '1.0.0'
            )
        ));
    }

    /**
     * List posts (optional endpoint for browsing)
     *
     * @param WP_REST_Request $request
     * @return WP_REST_Response
     */
    public function list_posts($request) {
        $per_page = $request->get_param('per_page');

        $posts = get_posts(array(
            'numberposts' => $per_page,
            'post_status' => 'publish'
        ));

        $result = array();
        foreach ($posts as $post) {
            $result[] = array(
                'id' => $post->ID,
                'title' => get_the_title($post),
                'slug' => $post->post_name,
                'url' => get_permalink($post),
                'date' => $post->post_date,
                'excerpt' => get_the_excerpt($post)
            );
        }

        return rest_ensure_response(array(
            'success' => true,
            'posts' => $result,
            'total' => count($result)
        ));
    }

    /**
     * Extract meaningful paragraphs from text content
     *
     * @param string $text_content
     * @return array
     */
    private function extract_paragraphs($text_content) {
        // Split by double newlines or periods followed by newlines
        $raw_paragraphs = preg_split('/\n\s*\n|\.\s*\n/', $text_content);

        $paragraphs = array();
        foreach ($raw_paragraphs as $para) {
            $para = trim($para);
            // Only include substantial paragraphs (more than 50 characters)
            if (strlen($para) > 50) {
                // Clean up spacing
                $para = preg_replace('/\s+/', ' ', $para);
                $paragraphs[] = $para;
            }
        }

        return array_values($paragraphs);
    }

    /**
     * Extract headings from HTML content
     *
     * @param string $content
     * @return array
     */
    private function extract_headings($content) {
        $headings = array();

        // Extract h1-h6 tags
        for ($level = 1; $level <= 6; $level++) {
            preg_match_all('/<h' . $level . '[^>]*>(.*?)<\/h' . $level . '>/i', $content, $matches);
            foreach ($matches[1] as $heading_text) {
                $clean_text = wp_strip_all_tags($heading_text);
                if (!empty($clean_text)) {
                    $headings[] = array(
                        'level' => $level,
                        'text' => $clean_text
                    );
                }
            }
        }

        return $headings;
    }

    /**
     * Extract image references from HTML content
     *
     * @param string $content
     * @return array
     */
    private function extract_images($content) {
        $images = array();

        // Extract img tags
        preg_match_all('/<img[^>]+>/i', $content, $img_matches);

        foreach ($img_matches[0] as $img_tag) {
            $img_data = array();

            // Extract src
            if (preg_match('/src=["\']([^"\']+)["\']/i', $img_tag, $src_match)) {
                $img_data['src'] = $src_match[1];
            }

            // Extract alt
            if (preg_match('/alt=["\']([^"\']+)["\']/i', $img_tag, $alt_match)) {
                $img_data['alt'] = $alt_match[1];
            }

            // Extract caption from figcaption if present
            if (preg_match('/<figcaption[^>]*>(.*?)<\/figcaption>/i', $content, $caption_match)) {
                $img_data['caption'] = wp_strip_all_tags($caption_match[1]);
            }

            if (!empty($img_data)) {
                $images[] = $img_data;
            }
        }

        return $images;
    }

    /**
     * Add CORS headers for cross-origin requests
     */
    public function add_cors_headers() {
        remove_filter('rest_pre_serve_request', 'rest_send_cors_headers');

        $normalize_origin = function($url) {
            $validated = wp_http_validate_url($url);
            if (!$validated) {
                return '';
            }

            $parts = wp_parse_url($validated);
            if (empty($parts['scheme']) || empty($parts['host'])) {
                return '';
            }

            $origin = $parts['scheme'] . '://' . $parts['host'];

            if (!empty($parts['port'])) {
                $port = (int) $parts['port'];
                if (80 !== $port && 443 !== $port) {
                    $origin .= ':' . $port;
                }
            }

            return $origin;
        };

        $candidates = array(
            home_url(),
            site_url(),
            'https://travelmemo.com',
            'https://www.travelmemo.com',
            'https://reisememo.ch',
            'https://www.reisememo.ch'
        );

        $allowed_origins = array();

        foreach ($candidates as $candidate) {
            $origin = $normalize_origin($candidate);
            if ($origin) {
                $allowed_origins[] = $origin;
            }
        }

        $allowed_origins = apply_filters('travelmemo_content_api_allowed_origins', array_unique($allowed_origins));

        add_filter('rest_pre_serve_request', function($value) use ($allowed_origins, $normalize_origin) {
            $origin_header = isset($_SERVER['HTTP_ORIGIN']) ? wp_unslash($_SERVER['HTTP_ORIGIN']) : '';

            if ($origin_header) {
                $origin = $normalize_origin($origin_header);

                if ($origin && in_array($origin, $allowed_origins, true)) {
                    header('Access-Control-Allow-Origin: ' . $origin);
                    header('Vary: Origin');
                }
            }

            header('Access-Control-Allow-Methods: GET, POST, OPTIONS');
            header('Access-Control-Allow-Headers: Content-Type, Authorization');

            return $value;
        });
    }
}

// Initialize the plugin
new Travelmemo_Content_API();

?>
