-- Wishlist table
CREATE TABLE IF NOT EXISTS wishlist (
  user_id INTEGER REFERENCES users(id),
  product_id INTEGER REFERENCES products(id),
  PRIMARY KEY (user_id, product_id)
);

-- Reviews table
CREATE TABLE IF NOT EXISTS reviews (
  id SERIAL PRIMARY KEY,
  user_id INTEGER REFERENCES users(id),
  product_id INTEGER REFERENCES products(id),
  rating INTEGER CHECK (rating BETWEEN 1 AND 5),
  comment TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
