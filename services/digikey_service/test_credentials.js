const axios = require('axios');

// DigiKey API configuration
const clientId = process.env.DIGIKEY_CLIENT_ID || 'ZT9LNhAQzYvQ9x06NlqtYGZoeRDdTsYEgK0JJDh0QlUs8Re4';
const clientSecret = process.env.DIGIKEY_CLIENT_SECRET || 'hQrLAiEuT73MvLmSjReuIGLvNdygRwb8E91P7UXYdK5CaUeyzYrFcKf6Gvvrjs25';
const tokenURL = 'https://api.digikey.com/v1/oauth2/token';

async function testCredentials() {
    try {
        console.log('Testing DigiKey API credentials...');
        console.log(`Client ID: ${clientId.substring(0, 5)}...`);

        const tokenData = {
            grant_type: 'client_credentials',
            client_id: clientId,
            client_secret: clientSecret
        };

        console.log(`Making token request to: ${tokenURL}`);

        const response = await axios.post(tokenURL, tokenData, {
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded'
            },
            timeout: 10000
        });

        console.log(`Token request successful. Response status: ${response.status}`);
        console.log(`Access token obtained: ${response.data.access_token.substring(0, 20)}...`);
        console.log('Credentials are valid!');

        return response.data.access_token;
    } catch (error) {
        console.error(`Failed to get DigiKey access token: ${error.message}`);
        if (error.response) {
            console.error(`Token request failed with status ${error.response.status}: ${JSON.stringify(error.response.data)}`);
        }
        return null;
    }
}

// Test search API with token
async function testSearchAPI(token) {
    try {
        console.log('Testing DigiKey Search API...');

        const searchURL = 'https://api.digikey.com/products/v4/search/keyword';
        const requestBody = {
            Keywords: 'resistor',
            RecordCount: 5,
            Includes: ["DigiKeyPartNumber", "ManufacturerPartNumber", "ProductDescription"]
        };

        console.log(`Making search request to: ${searchURL}`);

        const response = await axios.post(searchURL, requestBody, {
            headers: {
                'Authorization': `Bearer ${token}`,
                'X-DIGIKEY-Client-Id': clientId,
                'Content-Type': 'application/json',
            },
            timeout: 15000
        });

        console.log(`Search request successful. Response status: ${response.status}`);
        console.log(`Found ${response.data.Products ? response.data.Products.length : 0} products`);

    } catch (error) {
        console.error(`Failed to search DigiKey API: ${error.message}`);
        if (error.response) {
            console.error(`Search request failed with status ${error.response.status}: ${JSON.stringify(error.response.data)}`);
        }
    }
}

async function main() {
    const token = await testCredentials();
    if (token) {
        await testSearchAPI(token);
    }
}

main();
