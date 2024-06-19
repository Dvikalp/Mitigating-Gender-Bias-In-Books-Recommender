const fs = require('fs')
const csv = require('csv-parser')
const createCsvWriter = require('csv-writer').createObjectCsvWriter
const { getGender } = require('gender-detection-from-name')

const inputFilePath = 'unique_authors.csv';
const outputFilePath = 'output.csv';

const csvWriter = createCsvWriter({
    path: outputFilePath,
    header: [
        // { id: 'title', title: 'Title' },
        // { id: 'description', title: 'Description' },
        { id: 'authors', title: 'Author' }, 
        // { id: 'image', title: 'Image' },
        // { id: 'previewLink', title: 'PreviewLink' },
        // { id: 'publisher', title: 'Publisher' },
        // { id: 'publishedDate', title: 'PublishedDate' },
        // { id: 'infoLink', title: 'InfoLink' },
        // { id: 'categories', title: 'Categories' },
        // { id: 'ratingsCount', title: 'RatingsCount' },
        { id: 'gender', title: 'Gender' },
    ],
})

const results = [];

fs.createReadStream(inputFilePath)
    .pipe(csv())
    .on('data', (row) => {
        const fullName = row.Author;
        const firstName = getFirstName(fullName);
        let detectedGender;
        try {
            if(firstName=="Thomas"||firstName=="Richard"||firstName=="Nicolson"||firstName=="Arthur"||firstName=="Daniel"||firstName=="Ethan"||firstName=="Max"||firstName=="Alfred"||firstName=="Robert"||firstName=="William"||firstName=="Patrick"||firstName=="Samuel"||firstName=="Chris"||firstName=="Dan"||firstName=="Henry"||firstName=="Gaston"||firstName=="Joe"||firstName=="Paul"||firstName=="Benjamin"||firstName=="Robin"||firstName=="Charles"||firstName=="Marc"||firstName=="Martin"||firstName=="Terry"||firstName=="Gerome"||firstName=="Ernest"){
                detectedGender="male";
            }
            else{
                detectedGender = getGender(firstName);
            }
            
        } catch (error) {
            console.error(`Error detecting gender for "${firstName}": ${error.message}`);
            detectedGender = 'unknown';
        }
        console.log(`${firstName} - ${detectedGender}\n`)
        results.push({
            // title: row.Title,
            // description: row.description,
            authors: row.Author,
            // image: row.image,
            // previewLink: row.previewLink,
            // publisher: row.publisher,
            // publishedDate: row.publishedDate,
            // infoLink: row.infoLink,
            // categories: row.categories,
            // ratingsCount: row.ratingsCount,
            gender: detectedGender,
        })
    })
    .on('end', () => {
        csvWriter.writeRecords(results)
            .then(() => console.log("CSV file successfully written with gender information."))
    })

function getFirstName(fullName) {
    // const withoutBrackets= fullName.slice(2,-2);
    const parts=fullName.split(' ');
    return parts[0];
}