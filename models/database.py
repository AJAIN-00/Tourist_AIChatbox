import sqlite3
import os
from contextlib import contextmanager

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'tourism.db')

@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def init_db():
    with get_db() as conn:
        conn.executescript('''
            CREATE TABLE IF NOT EXISTS places (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                city TEXT NOT NULL,
                description TEXT,
                history TEXT,
                entry_fee TEXT,
                opening_time TEXT,
                closing_time TEXT,
                best_season TEXT,
                latitude REAL,
                longitude REAL,
                nearby_attractions TEXT,
                nearby_restaurants TEXT,
                nearby_hotels TEXT,
                image_url TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS chat_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                user_message TEXT,
                bot_response TEXT,
                language TEXT DEFAULT 'en',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS admin_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        ''')

def seed_data():
    places = [
        # Chennai (5 places)
        {
            'name': 'Marina Beach',
            'city': 'Chennai',
            'description': 'Marina Beach is the longest natural urban beach in India, stretching 13 km along the Bay of Bengal. It is a vibrant hub of activity, especially in the evenings, with iconic statues, a lighthouse, and numerous local food stalls selling local snacks like sundal and murukku.',
            'history': 'Developed by Governor Mountstuart Elphinstone Grant Duff in the 1880s, Marina Beach has been a central landmark of Chennai (formerly Madras) for over a century. The promenade is dotted with statues of prominent figures from Tamil history and culture, including Thiruvalluvar, Kannagi, and Mahatma Gandhi.',
            'entry_fee': 'Free',
            'opening_time': 'Open 24 hours',
            'closing_time': 'Open 24 hours',
            'best_season': 'November to February',
            'latitude': 13.0500,
            'longitude': 80.2824,
            'nearby_attractions': 'San Thome Cathedral, Vivekananda House, Fort St. George',
            'nearby_restaurants': 'Nair Mess, Saravana Bhavan, Ratna Cafe',
            'nearby_hotels': 'The Leela Palace, Taj Coromandel, ITC Grand Chola'
        },
        {
            'name': 'Fort St George',
            'city': 'Chennai',
            'description': 'Fort St. George is the first English fortress in India, founded in 1644. It is a historic stronghold that currently houses the Tamil Nadu Legislative Assembly and the Fort Museum, which displays rich colonial-era artifacts, weapons, and paintings.',
            'history': 'The construction of the fort marked the birth of modern Chennai. It was built by the British East India Company to establish a trading post. St. Mary\'s Church inside the fort is the oldest Anglican church in India, and the fort\'s flagstaff is one of the tallest in the country.',
            'entry_fee': '₹20 (Indians), ₹250 (Foreigners)',
            'opening_time': '09:00 AM',
            'closing_time': '05:00 PM',
            'best_season': 'November to February',
            'latitude': 13.0797,
            'longitude': 80.2883,
            'nearby_attractions': 'Marina Beach, High Court Complex, Chennai Port',
            'nearby_restaurants': 'National Restaurant, Annalakshmi Restaurant, Buhari',
            'nearby_hotels': 'Taj Club House, Vivanta Chennai IT Expressway, Radisson Blu'
        },
        {
            'name': 'Kapaleeshwarar Temple',
            'city': 'Chennai',
            'description': 'Kapaleeshwarar Temple is a highly revered Hindu temple dedicated to Lord Shiva, located in Mylapore, Chennai. It features a spectacular Dravidian tower (Gopuram) covered with thousands of detailed colorful stucco figures.',
            'history': 'The original temple was constructed by the Pallava dynasty in the 7th century, but was destroyed by Portuguese invaders. The current structure was rebuilt by the Vijayanagara rulers in the 16th century. It is famous for the legends of Goddess Parvati worshipping Shiva in the form of a peacock (Mayil in Tamil), giving Mylapore its name.',
            'entry_fee': 'Free',
            'opening_time': '05:00 AM',
            'closing_time': '09:00 PM',
            'best_season': 'October to March (especially during the Arubathimoovar festival)',
            'latitude': 13.0339,
            'longitude': 80.2692,
            'nearby_attractions': 'San Thome Cathedral, Mylapore Tank, Luz Church',
            'nearby_restaurants': 'Mylapore Ganapathy\'s, Rayar\'s Mess, Karpagambal Mess',
            'nearby_hotels': 'Savera Hotel, Clarion Hotel President, The Raintree'
        },
        {
            'name': 'Valluvar Kottam',
            'city': 'Chennai',
            'description': 'Valluvar Kottam is a magnificent chariot-shaped monument built in honor of the classical Tamil poet, philosopher, and saint Thiruvalluvar. The monument houses a massive auditorium and a 39-meter-high stone chariot representing the poet\'s legacy.',
            'history': 'Inaugurated in 1976 by then Chief Minister M. Karunanidhi, the monument was designed to immortalize Thiruvalluvar\'s epic work, the Thirukkural. All 1,330 couplets (Kurals) are inscribed on the granite pillars lining the main corridor.',
            'entry_fee': '₹10 (Adults), ₹5 (Children)',
            'opening_time': '08:30 AM',
            'closing_time': '05:30 PM',
            'best_season': 'November to February',
            'latitude': 13.0560,
            'longitude': 80.2440,
            'nearby_attractions': 'Semmozhi Poonga, Nungambakkam Shopping Street, Spencer Plaza',
            'nearby_restaurants': 'Mathsya, Cascade, The Park Restaurants',
            'nearby_hotels': 'The Park Chennai, Taj Coromandel, Ambassador Pallava'
        },
        {
            'name': 'Guindy National Park',
            'city': 'Chennai',
            'description': 'Guindy National Park is India\'s eighth-smallest national park and unique for being situated entirely inside a metropolitan city. It protects a dry evergreen forest habitat and is home to blackbucks, spotted deer, jackals, and over 130 species of birds.',
            'history': 'Originally a game reserve owned by British resident Gilbert Rodericks, the property was purchased by the Madras Government in the early 20th century. A portion was later declared a National Park in 1978. It borders the historic Raj Bhavan and IIT Madras campus.',
            'entry_fee': '₹20 (Adults), ₹10 (Children)',
            'opening_time': '09:00 AM',
            'closing_time': '05:30 PM',
            'best_season': 'October to May',
            'latitude': 13.0067,
            'longitude': 80.2206,
            'nearby_attractions': 'Chennai Snake Park, Children\'s Park, Birla Planetarium',
            'nearby_restaurants': 'Prems Graama Bhojanam, Madras Pavilion, Absolute Barbecues',
            'nearby_hotels': 'Park Hyatt Chennai, ITC Grand Chola, Feathers OMR'
        },
        
        # Coimbatore (5 places)
        {
            'name': 'Isha Yoga Center',
            'city': 'Coimbatore',
            'description': 'Isha Yoga Center is a prominent spiritual sanctuary founded by Sadhguru. Set at the foothills of the Velliangiri Mountains, it features the consecrated Dhyanalinga and Theerthakunds (subterranean water pools) for spiritual purification.',
            'history': 'Established in 1992 by Sadhguru Jaggi Vasudev, the center has grown into a global destination for inner growth and yoga sciences. It was built using ancient temple science principles without cement or steel in its core structures.',
            'entry_fee': 'Free',
            'opening_time': '06:00 AM',
            'closing_time': '08:00 PM',
            'best_season': 'September to March',
            'latitude': 10.9267,
            'longitude': 76.8536,
            'nearby_attractions': 'Adiyogi Statue, Siruvani Waterfalls, Velliangiri Hills Trail',
            'nearby_restaurants': 'Isha Peetham Cafe, Sree Annapoorna, Haribhavanam',
            'nearby_hotels': 'Isha Cottage (prior booking required), Sterling Anaikatti, Welcomhotel by ITC'
        },
        {
            'name': 'Adiyogi Statue',
            'city': 'Coimbatore',
            'description': 'The Adiyogi Statue is a majestic 112-foot steel bust of Lord Shiva, recognized by the Guinness World Records as the largest bust sculpture in the world. It is designed to inspire inner well-being through yoga.',
            'history': 'Inaugurated on Mahashivratri in 2017 by the Prime Minister of India, the statue represents Shiva as the first yogi (Adiyogi) who transmitted the yogic sciences to the Saptarishis (seven sages). The height of 112 feet symbolizes the 112 methods to attain liberation.',
            'entry_fee': 'Free',
            'opening_time': '06:00 AM',
            'closing_time': '08:00 PM',
            'best_season': 'September to March (spectacular during Mahashivratri)',
            'latitude': 10.9267,
            'longitude': 76.8536,
            'nearby_attractions': 'Isha Yoga Center, Dhyanalinga, Velliangiri Hill Temple',
            'nearby_restaurants': 'Nalapakas, Sree Gowrishankar, local coconut water stalls',
            'nearby_hotels': 'Residency Towers Coimbatore, Radisson Blu, Zone by The Park'
        },
        {
            'name': 'Kovai Kutralam',
            'city': 'Coimbatore',
            'description': 'Kovai Kutralam, also known as Siruvani Waterfalls, is a breathtaking natural waterfall located in a dense forest reserve. The water is sourced from the Siruvani River, widely celebrated for having some of the sweetest mineral water in the world.',
            'history': 'Managed by the Tamil Nadu Forest Department, this area has been protected for centuries to preserve the Siruvani Dam and catchment area. Access is restricted and requires a forest department shuttle ride, ensuring the ecosystem remains pristine.',
            'entry_fee': '₹50 (includes eco-tourism bus ride)',
            'opening_time': '10:00 AM',
            'closing_time': '03:00 PM',
            'best_season': 'June to October (post-monsoon)',
            'latitude': 10.9392,
            'longitude': 76.6890,
            'nearby_attractions': 'Siruvani Dam, Isha Yoga Center, Perur Pateeswarar Temple',
            'nearby_restaurants': 'Hotel Gowri Krishna, Local forest checkpost tea stalls',
            'nearby_hotels': 'Dugar Resorts, Coco Lagoon, Fairfield by Marriott'
        },
        {
            'name': 'Marudhamalai Temple',
            'city': 'Coimbatore',
            'description': 'Marudhamalai Temple is an ancient hilltop temple dedicated to Lord Murugan (Kartikeya). Situated on a granite hill part of the Western Ghats, the temple offers panoramic views of the plains below and is famous for its serene spiritual vibes.',
            'history': 'Believed to be over 1,200 years old, the temple has references in Sangam literature. The hill is named after the Marutham trees that grow abundantly here. It is historically linked with ancient Siddhar sages who used the herbal plants on the hill for medicinal purposes.',
            'entry_fee': 'Free (₹100 for special darshan, ₹20 for hill bus)',
            'opening_time': '06:00 AM',
            'closing_time': '08:30 PM',
            'best_season': 'September to March',
            'latitude': 11.0478,
            'longitude': 76.8972,
            'nearby_attractions': 'Perur Pateeswarar Temple, Eachanari Vinayagar Temple, Gedee Car Museum',
            'nearby_restaurants': 'Sree Annapoorna Sree Gowrishankar, Sri Anandhaas, Haribhavanam',
            'nearby_hotels': 'Radha Regent, Heritage Inn, Vivanta Coimbatore'
        },
        {
            'name': 'VOC Park',
            'city': 'Coimbatore',
            'description': 'VOC Park and Zoo is a popular central recreational park named after freedom fighter V.O. Chidambaram Pillai. The park is a major family attraction featuring a children\'s play area, a mini-zoo, a toy train, and a garden with models of prehistoric animals.',
            'history': 'Established by the Coimbatore Municipal Corporation in the post-independence era, the park was dedicated to VOC (The Tamil Helmsman), who established the first indigenous shipping service during the British rule. It has served as a cultural hub hosting Republic Day and Independence Day parades.',
            'entry_fee': '₹20 (Adults), ₹10 (Children)',
            'opening_time': '04:00 PM',
            'closing_time': '07:30 PM (Closes later on Sundays)',
            'best_season': 'Year-round',
            'latitude': 11.0024,
            'longitude': 76.9787,
            'nearby_attractions': 'Gedee Car Museum, Brookefields Mall, Eachanari Temple',
            'nearby_restaurants': 'The French Door, Sree Gowrishankar, Kove',
            'nearby_hotels': 'Hotel City Tower, The Residency Towers, Welcomhotel'
        },
        
        # Kanyakumari (5 places)
        {
            'name': 'Vivekananda Rock Memorial',
            'city': 'Kanyakumari',
            'description': 'The Vivekananda Rock Memorial is an iconic monument built on a small rock island off the coast of Kanyakumari. It is built at the confluence of the Arabian Sea, the Bay of Bengal, and the Indian Ocean, commemorating Swami Vivekananda\'s visit and meditation.',
            'history': 'Swami Vivekananda swam to this rock in December 1892 and meditated for three days, realizing his life\'s mission before traveling to the Parliament of Religions in Chicago. The memorial was constructed between 1964 and 1970 through national fundraising led by Eknath Ranade.',
            'entry_fee': '₹20 (Entry), ₹50 (Ferry ticket)',
            'opening_time': '08:00 AM',
            'closing_time': '04:00 PM',
            'best_season': 'October to March',
            'latitude': 8.0778,
            'longitude': 77.5530,
            'nearby_attractions': 'Thiruvalluvar Statue, Kumari Amman Temple, Gandhi Memorial',
            'nearby_restaurants': 'Hotel Saravana Bhavan, The Ocean Restaurant, Sea View Restaurant',
            'nearby_hotels': 'Sparsa Resorts, Hotel Tri Sea, Hotel Maadhini'
        },
        {
            'name': 'Thiruvalluvar Statue',
            'city': 'Kanyakumari',
            'description': 'The Thiruvalluvar Statue is a colossal 133-foot-tall stone sculpture of the legendary Tamil poet and philosopher Thiruvalluvar, located on an island rock adjacent to the Vivekananda Rock Memorial.',
            'history': 'Created by renowned sculptor V. Ganapati Sthapati, the statue was inaugurated on January 1, 2000. Its height of 133 feet symbolizes the 133 chapters of the Thirukkural. The 38-foot pedestal represents the chapters on Virtue, while the 95-foot statue represents Wealth and Love.',
            'entry_fee': 'Included in Ferry ticket',
            'opening_time': '08:00 AM',
            'closing_time': '04:00 PM',
            'best_season': 'October to March',
            'latitude': 8.0764,
            'longitude': 77.5519,
            'nearby_attractions': 'Vivekananda Rock Memorial, Sunset Point, Kanyakumari Temple',
            'nearby_restaurants': 'Archana Restaurant, Sea Queen, Sangam Hotel Restaurant',
            'nearby_hotels': 'The Seashore Hotel, Hotel Singaar International, Hotel Temple Citie'
        },
        {
            'name': 'Gandhi Memorial',
            'city': 'Kanyakumari',
            'description': 'The Gandhi Memorial Mandapam is a unique monument built in the style of Orissan temples. It marks the spot where the urn containing Mahatma Gandhi\'s ashes was kept for public viewing before immersion in the sea.',
            'history': 'Built in 1956, the memorial is architecturally designed so that on October 2 (Mahatma Gandhi\'s birthday), the first rays of the sun fall directly through an opening in the roof onto the exact spot where the ashes were kept.',
            'entry_fee': 'Free (Donations accepted)',
            'opening_time': '07:00 AM',
            'closing_time': '07:00 PM',
            'best_season': 'October to March',
            'latitude': 8.0815,
            'longitude': 77.5552,
            'nearby_attractions': 'Kanyakumari Beach, Kamarajar Mani Mantapam, Kumari Amman Temple',
            'nearby_restaurants': 'Hotel Saravana, Triveni Restaurant, Sea View',
            'nearby_hotels': 'Hotel Sea View, Sparsa Resorts, Hotel Tamil Nadu (TTDC)'
        },
        {
            'name': 'Sunset Point',
            'city': 'Kanyakumari',
            'description': 'Sunset Point is a scenic viewing area on the Kanyakumari coast. It offers a spectacular, unobstructed view of the sun setting over the vast ocean, and is famous during full moon nights when the sun sets and the moon rises simultaneously.',
            'history': 'Kanyakumari is one of the few places in India where one can view both the sunrise and sunset from the same beach. Over centuries, this geographic marvel has attracted travelers, poets, and pilgrims from all over the world, finding mentions in Sangam scriptures.',
            'entry_fee': 'Free',
            'opening_time': 'Open 24 hours',
            'closing_time': 'Open 24 hours',
            'best_season': 'November to February',
            'latitude': 8.0833,
            'longitude': 77.5333,
            'nearby_attractions': 'Gandhi Memorial, Kanyakumari Beach, Wax Museum',
            'nearby_restaurants': 'Ocean Heritage, Beachside snack stalls, Coral Reef',
            'nearby_hotels': 'Hotel Seashore, Hotel Tri Sea, Sparsa Resorts'
        },
        {
            'name': 'Kanyakumari Beach',
            'city': 'Kanyakumari',
            'description': 'Kanyakumari Beach is a gorgeous shoreline at the southernmost tip of the Indian subcontinent. The beach is famous for its unique multicolored sands and is a sacred bathing site due to the holy confluence of three seas (Triveni Sangam).',
            'history': 'The town and beach are named after the Goddess Kanya Kumari (the Virgin Goddess), a form of Parvati. According to mythology, the colorful sand represents the uncooked grains meant for the wedding of the Goddess and Shiva, which never took place.',
            'entry_fee': 'Free',
            'opening_time': 'Open 24 hours',
            'closing_time': 'Open 24 hours',
            'best_season': 'October to March',
            'latitude': 8.0800,
            'longitude': 77.5550,
            'nearby_attractions': 'Kumari Amman Temple, Vivekananda Rock Ferry, Gandhi Memorial',
            'nearby_restaurants': 'Hotel Sangam Restaurant, Local fish stalls, Saravana Bhavan',
            'nearby_hotels': 'Hotel Maadhini, The Seashore Hotel, Sparsa Resorts'
        }
    ]

    with get_db() as conn:
        # Check if already seeded
        cursor = conn.execute("SELECT COUNT(*) FROM places")
        count = cursor.fetchone()[0]
        if count == 0:
            for p in places:
                conn.execute('''
                    INSERT INTO places (
                        name, city, description, history, entry_fee, 
                        opening_time, closing_time, best_season, 
                        latitude, longitude, nearby_attractions, 
                        nearby_restaurants, nearby_hotels
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    p['name'], p['city'], p['description'], p['history'], p['entry_fee'],
                    p['opening_time'], p['closing_time'], p['best_season'],
                    p['latitude'], p['longitude'], p['nearby_attractions'],
                    p['nearby_restaurants'], p['nearby_hotels']
                ))
            print("Successfully seeded 15 places!")
        else:
            print("Places table already seeded.")

        # Seed default admin user (username: admin, password: admin123)
        import hashlib
        cursor_admin = conn.execute("SELECT COUNT(*) FROM admin_users")
        admin_count = cursor_admin.fetchone()[0]
        if admin_count == 0:
            pwd_hash = hashlib.sha256('admin123'.encode()).hexdigest()
            conn.execute('INSERT INTO admin_users (username, password_hash) VALUES (?, ?)', ('admin', pwd_hash))
            print("Default admin account seeded.")
        else:
            print("Admin account already exists.")

def get_all_places(city=None):
    with get_db() as conn:
        if city:
            cursor = conn.execute('SELECT * FROM places WHERE LOWER(city) = LOWER(?)', (city,))
        else:
            cursor = conn.execute('SELECT * FROM places')
        return [dict(row) for row in cursor.fetchall()]

def get_place_by_id(place_id):
    with get_db() as conn:
        cursor = conn.execute('SELECT * FROM places WHERE id = ?', (place_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

def save_chat(session_id, user_message, bot_response, language):
    with get_db() as conn:
        conn.execute('''
            INSERT INTO chat_history (session_id, user_message, bot_response, language)
            VALUES (?, ?, ?, ?)
        ''', (session_id, user_message, bot_response, language))

def verify_admin(username, password):
    import hashlib
    with get_db() as conn:
        cursor = conn.execute('SELECT password_hash FROM admin_users WHERE username = ?', (username,))
        row = cursor.fetchone()
        if row:
            stored_hash = row['password_hash']
            input_hash = hashlib.sha256(password.encode()).hexdigest()
            return stored_hash == input_hash
        return False

def add_place(data):
    with get_db() as conn:
        conn.execute('''
            INSERT INTO places (
                name, city, description, history, entry_fee, 
                opening_time, closing_time, best_season, 
                latitude, longitude, nearby_attractions, 
                nearby_restaurants, nearby_hotels, image_url
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data['name'], data['city'], data.get('description'), data.get('history'),
            data.get('entry_fee'), data.get('opening_time'), data.get('closing_time'),
            data.get('best_season'), data.get('latitude'), data.get('longitude'),
            data.get('nearby_attractions'), data.get('nearby_restaurants'), data.get('nearby_hotels'),
            data.get('image_url')
        ))

def update_place(place_id, data):
    with get_db() as conn:
        # Build update query — only update image_url if a new one was provided (or explicitly cleared)
        if data.get('image_url') is not None:
            conn.execute('''
                UPDATE places SET 
                    name = ?, city = ?, description = ?, history = ?, entry_fee = ?, 
                    opening_time = ?, closing_time = ?, best_season = ?, 
                    latitude = ?, longitude = ?, nearby_attractions = ?, 
                    nearby_restaurants = ?, nearby_hotels = ?, image_url = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (
                data['name'], data['city'], data.get('description'), data.get('history'),
                data.get('entry_fee'), data.get('opening_time'), data.get('closing_time'),
                data.get('best_season'), data.get('latitude'), data.get('longitude'),
                data.get('nearby_attractions'), data.get('nearby_restaurants'), data.get('nearby_hotels'),
                data.get('image_url'), place_id
            ))
        else:
            conn.execute('''
                UPDATE places SET 
                    name = ?, city = ?, description = ?, history = ?, entry_fee = ?, 
                    opening_time = ?, closing_time = ?, best_season = ?, 
                    latitude = ?, longitude = ?, nearby_attractions = ?, 
                    nearby_restaurants = ?, nearby_hotels = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (
                data['name'], data['city'], data.get('description'), data.get('history'),
                data.get('entry_fee'), data.get('opening_time'), data.get('closing_time'),
                data.get('best_season'), data.get('latitude'), data.get('longitude'),
                data.get('nearby_attractions'), data.get('nearby_restaurants'), data.get('nearby_hotels'),
                place_id
            ))

def delete_place(place_id):
    with get_db() as conn:
        conn.execute('DELETE FROM places WHERE id = ?', (place_id,))
