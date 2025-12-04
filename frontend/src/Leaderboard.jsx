import React, { useState, useEffect } from 'react';

const API_URL = 'http://localhost:5001/leaderboard';

// Utility function to map Category to a Tailwind CSS class
const getCategoryColor = (category) => {
    switch (category) {
        case 'Good':
            return 'bg-green-600'; // Green
        case 'Moderate':
            return 'bg-yellow-500'; // Yellow
        case 'Unhealthy for Sensitive Groups':
            return 'bg-orange-600'; // Orange
        case 'Unhealthy':
            return 'bg-red-600'; // Red
        case 'Very Unhealthy':
            return 'bg-purple-600'; // Purple
        case 'Hazardous':
            return 'bg-red-800';; // Maroon/Dark Red
        default:
            return 'bg-gray-400';
    }
};

const Leaderboard = () => {
    const [data, setData] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    const fetchData = async () => {
        try {
            const response = await fetch(API_URL);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const result = await response.json();
            setData(result);
        } catch (e) {
            setError("Could not connect to Aggregator API. Is 'python aggregator/app.py' running?");
            console.error(e);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchData(); // Fetch immediately

        // Set up polling (e.g., every 30 seconds)
        const interval = setInterval(fetchData, 30000); 

        // Cleanup on component unmount
        return () => clearInterval(interval);
    }, []);

    if (loading) return <div className="text-center p-8 text-xl text-gray-400">Loading data from Smog Signal Network...</div>;
    if (error) return <div className="text-center p-8 text-red-500 font-bold">{error}</div>;

    return (
        <div className="container mx-auto p-4">
            <h1 className="text-4xl font-bold text-gray-800 mb-6 text-center">
                🌍 Global PM2.5 Leaderboard
            </h1>
            <p className="text-center text-gray-600 mb-8">
                Air Quality data sorted by raw PM2.5 concentration (worst first). Auto-refreshes every 30 seconds.
            </p>
            <p className="text-center text-gray-600 mb-8">
                Cities that have population above 500k and has PM2.5 sensor setup by OPENAQ.
            </p>
            
            <div className="bg-white shadow-xl rounded-lg overflow-hidden">
                <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                        <tr>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Rank</th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">City</th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Pollutant Value</th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Category</th>
                        </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                        {data.map((city, index) => (
                            <tr key={city.location_id} className="hover:bg-gray-50">
                                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{index + 1}</td>
                                <td className="px-6 py-4 whitespace-nowrap text-sm font-bold text-gray-900">{city.city_name}</td>
                                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-700">
                                    {/* The Aggregator sends 'value' as the raw concentration */}
                                    <span className="font-semibold text-lg">{city.value ? city.value.toFixed(2) : 'N/A'}</span>
                                    <span className="text-xs ml-1">{city.unit || 'µg/m³'}</span>
                                </td>
                                <td className="px-6 py-4 whitespace-nowrap">
                                    {/* Color-coded category pill */}
                                    <span className={`px-3 inline-flex text-xs leading-5 font-semibold rounded-full ${getCategoryColor(city.aq_category)} text-white shadow-md`}>
                                        {city.aq_category || 'N/A'}
                                    </span>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
};

export default Leaderboard;