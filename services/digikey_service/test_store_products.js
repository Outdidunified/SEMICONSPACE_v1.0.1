const DigiKeyService = require('./services/DigiKeyService');

async function testStoreProducts() {
    const digiKeyService = new DigiKeyService();

    // Create test products
    const testProducts = [
        {
            productId: 'test_product_1',
            name: 'Test Product 1',
            description: 'Test product for duplication check',
            price: 10.99,
            query: 'test',
            manufacturer: 'Test Manufacturer',
            manufacturerPartNumber: 'TP-001',
            digiKeyPartNumber: 'DK-TP-001',
            quantityAvailable: 100
        },
        {
            productId: 'test_product_2',
            name: 'Test Product 2',
            description: 'Another test product',
            price: 15.99,
            query: 'test',
            manufacturer: 'Test Manufacturer',
            manufacturerPartNumber: 'TP-002',
            digiKeyPartNumber: 'DK-TP-002',
            quantityAvailable: 50
        }
    ];

    console.log('Testing storeProducts method...');

    // Store products for the first time
    console.log('First store operation:');
    const result1 = await digiKeyService.storeProducts(testProducts);
    console.log(`Inserted: ${result1.insertedCount}, Skipped: ${result1.skippedCount}`);

    // Store the same products again
    console.log('Second store operation (should skip existing products):');
    const result2 = await digiKeyService.storeProducts(testProducts);
    console.log(`Inserted: ${result2.insertedCount}, Skipped: ${result2.skippedCount}`);

    console.log('Test completed.');
}

testStoreProducts().catch(console.error);
