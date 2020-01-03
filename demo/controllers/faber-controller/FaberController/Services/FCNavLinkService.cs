using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Text.Json;
using FaberController.Models;
using Microsoft.AspNetCore.Hosting;

namespace FaberController.Services
{
    public class FCNavLinkService
    {
        public FCNavLinkService(IWebHostEnvironment webHostEnvironment)
        {
            _webHostEnvironment = webHostEnvironment;
        }

        private IWebHostEnvironment _webHostEnvironment { get; }

        private string _jsonFileName
        {
            get { return Path.Combine(_webHostEnvironment.WebRootPath, "data", "nav_links.json"); }
        }

        public IEnumerable<NavLink> GetNavLinks()
        {
            using var jsonFileReader = File.OpenText(_jsonFileName);
            return JsonSerializer.Deserialize<NavLink[]>(jsonFileReader.ReadToEnd(),
                new JsonSerializerOptions
                {
                    PropertyNameCaseInsensitive = true
                });
        }
    }
}
